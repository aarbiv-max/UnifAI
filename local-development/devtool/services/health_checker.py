"""Application service: health checking and status dashboard."""

from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

from devtool.domain.models import (
    ContainerStatus,
    InfraHealth,
    Service,
    ServiceHealth,
    StatusIssue,
)
from devtool.domain.registry import Registry
from devtool.ports.container_runtime import ContainerRuntime
from devtool.ports.session_manager import SessionManager


# ---------------------------------------------------------------------------
# Low-level probes
# ---------------------------------------------------------------------------

def check_port(host: str, port: int, timeout: float = 2.0) -> tuple[bool, float | None]:
    """Probe a TCP port.  Returns (is_open, response_time_ms)."""
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed = (time.monotonic() - start) * 1000
            return True, round(elapsed, 1)
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False, None


def check_http(
    host: str, port: int, path: str = "/", timeout: float = 3.0,
) -> tuple[bool, float | None]:
    """HTTP GET against a health endpoint.  Returns (is_ok, response_time_ms)."""
    url = f"http://{host}:{port}{path}"
    start = time.monotonic()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout):
            elapsed = (time.monotonic() - start) * 1000
            return True, round(elapsed, 1)
    except (urllib.error.URLError, OSError, TimeoutError):
        return False, None


# ---------------------------------------------------------------------------
# Single-entity checks
# ---------------------------------------------------------------------------

def check_service(registry: Registry, service_name: str) -> ServiceHealth:
    """Check if a single service's port is reachable."""
    svc = registry.get_service(service_name)
    if not svc.port:
        return ServiceHealth(
            name=svc.name, status="no port", port=None, port_open=False,
        )

    host = _resolve_host(svc)
    is_open, tcp_ms = check_port(host, svc.port)

    if not is_open:
        return ServiceHealth(
            name=svc.name, status="DOWN", port=svc.port, port_open=False,
        )

    http_ok = False
    response_ms = tcp_ms
    if svc.health_endpoint:
        http_ok, http_ms = check_http(host, svc.port, svc.health_endpoint)
        if http_ms is not None:
            response_ms = http_ms

    status = "healthy" if (http_ok or not svc.health_endpoint) else "unhealthy"
    return ServiceHealth(
        name=svc.name,
        status=status,
        port=svc.port,
        port_open=True,
        http_healthy=http_ok,
        response_time_ms=response_ms,
    )


def check_infra(
    component, runtime: ContainerRuntime,
) -> InfraHealth:
    """Check a single infrastructure component."""
    st = runtime.status(component)
    uptime = runtime.container_uptime(component) if st is ContainerStatus.RUNNING else None
    port = _parse_host_port(component.ports[0]) if component.ports else None
    return InfraHealth(
        name=component.name,
        label=component.label,
        port=port,
        status=st,
        uptime=uptime,
    )


# ---------------------------------------------------------------------------
# Full dashboard
# ---------------------------------------------------------------------------

SESSION_NAME = "unifai-dev"


def build_dashboard(
    registry: Registry,
    runtime: ContainerRuntime,
    session: SessionManager,
) -> tuple[list[InfraHealth], list[ServiceHealth], list[StatusIssue]]:
    """Collect health for every component and produce actionable issues."""

    infra_results = [
        check_infra(comp, runtime)
        for comp in registry.all_infra()
    ]

    pane_contents = session.pane_contents(SESSION_NAME)
    pane_mapping = match_panes_to_services(registry.all_services(), pane_contents)

    service_results: list[ServiceHealth] = []
    for svc in registry.all_services():
        health = check_service(registry, svc.name)
        tmux_pane = pane_mapping.get(svc.name)
        service_results.append(ServiceHealth(
            name=health.name,
            status=health.status,
            port=health.port,
            port_open=health.port_open,
            http_healthy=health.http_healthy,
            response_time_ms=health.response_time_ms,
            tmux_pane=f"tmux:{tmux_pane}" if tmux_pane else None,
            error=health.error,
        ))

    issues = _analyze_issues(registry, infra_results, service_results)
    return infra_results, service_results, issues


def render_dashboard(
    infra_results: list[InfraHealth],
    service_results: list[ServiceHealth],
    issues: list[StatusIssue],
) -> None:
    """Print a human-friendly status dashboard to stdout."""

    print()
    print("  INFRASTRUCTURE")
    for ih in infra_results:
        port_str = f":{ih.port}" if ih.port else ""
        if ih.status is ContainerStatus.RUNNING:
            uptime_str = f"  (up {ih.uptime})" if ih.uptime else ""
            print(f"  \u2714 {ih.label:<14}{port_str:<10}running{uptime_str}")
        elif ih.status is ContainerStatus.STOPPED:
            print(f"  \u2716 {ih.label:<14}{port_str:<10}STOPPED")
        else:
            print(f"  \u2716 {ih.label:<14}{port_str:<10}NOT CREATED")

    print()
    print("  SERVICES")
    for sh in service_results:
        port_str = f":{sh.port}" if sh.port else ""
        pane_str = f"  {sh.tmux_pane}" if sh.tmux_pane else ""
        if sh.status == "healthy":
            rt = f"  ({sh.response_time_ms}ms)" if sh.response_time_ms else ""
            print(f"  \u2714 {sh.name:<14}{port_str:<10}healthy{rt}{pane_str}")
        elif sh.status == "no port":
            status_label = "worker" if pane_str else "no port"
            print(f"  \u2500 {sh.name:<14}{'':<10}{status_label}{pane_str}")
        elif sh.status == "unhealthy":
            rt = f"  ({sh.response_time_ms}ms)" if sh.response_time_ms else ""
            print(f"  \u26a0 {sh.name:<14}{port_str:<10}unhealthy{rt}{pane_str}")
        else:
            print(f"  \u2716 {sh.name:<14}{port_str:<10}DOWN{pane_str}")

    if issues:
        print()
        print("  ISSUES")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue.description}")
            print(f"     Fix: {issue.fix}")
    print()


# ---------------------------------------------------------------------------
# Issue analysis
# ---------------------------------------------------------------------------

def _analyze_issues(
    registry: Registry,
    infra_results: list[InfraHealth],
    service_results: list[ServiceHealth],
) -> list[StatusIssue]:
    """Cross-reference infra and service health to generate actionable issues."""
    issues: list[StatusIssue] = []

    stopped_infra = {
        ih.name for ih in infra_results
        if ih.status is not ContainerStatus.RUNNING
    }

    for infra_name in stopped_infra:
        affected = [
            svc.name
            for svc in registry.all_services()
            if infra_name in svc.infrastructure
        ]
        comp = registry.get_infra(infra_name)
        desc = f"{comp.label} stopped"
        if affected:
            desc += f" \u2192 {' + '.join(affected)} affected"
        issues.append(StatusIssue(
            description=desc,
            fix=f"unifai-dev infra start {infra_name}",
            affected=affected,
        ))

    infra_caused = set()
    for issue in issues:
        infra_caused.update(issue.affected)

    for sh in service_results:
        if sh.status in ("healthy", "no port"):
            continue
        if sh.name in infra_caused:
            continue
        if sh.status == "unhealthy":
            issues.append(StatusIssue(
                description=f"{sh.name} health endpoint failing on port {sh.port}",
                fix=f"unifai-dev restart {sh.name}",
                affected=[sh.name],
            ))
        else:
            issues.append(StatusIssue(
                description=f"{sh.name} not responding on port {sh.port}",
                fix=f"unifai-dev restart {sh.name}",
                affected=[sh.name],
            ))

    return issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_host(svc: Service) -> str:
    host = svc.host or "127.0.0.1"
    if host == "0.0.0.0":
        host = "127.0.0.1"
    return host


def _parse_host_port(port_mapping: str) -> int | None:
    """Extract the host port from a mapping like ``"6379:6379"``."""
    try:
        return int(port_mapping.split(":")[0])
    except (ValueError, IndexError):
        return None


def match_panes_to_services(
    services: list[Service],
    pane_contents: dict[str, str],
) -> dict[str, str]:
    """Match services to tmux pane refs by scanning pane content for
    service directory names or launch commands."""
    mapping: dict[str, str] = {}
    used_panes: set[str] = set()

    for svc in services:
        svc_dir = str(svc.directory)
        for pane_ref, content in pane_contents.items():
            if pane_ref in used_panes:
                continue
            if svc_dir in content or svc.name in content:
                mapping[svc.name] = pane_ref
                used_panes.add(pane_ref)
                break
    return mapping
