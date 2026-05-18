"""Application service: health checking and status dashboard.

Orchestrates health probing via the HealthProbe port (no direct I/O).
"""

from __future__ import annotations

import re

from devtool.domain.models import (
    ContainerStatus,
    InfraComponent,
    InfraHealth,
    Service,
    ServiceHealth,
    ServiceStatus,
    StatusIssue,
)
from devtool.domain.registry import Registry
from devtool.ports.container_runtime import ContainerRuntime
from devtool.ports.health_probe import HealthProbe
from devtool.ports.session_manager import SessionManager
from devtool.services.constants import SESSION_NAME


class HealthChecker:
    """Checks service and infrastructure health via an injected HealthProbe."""

    def __init__(self, probe: HealthProbe) -> None:
        self._probe = probe

    def check_service(self, registry: Registry, service_name: str) -> ServiceHealth:
        return _check_service(registry, service_name, self._probe)

    def build_dashboard(
        self,
        registry: Registry,
        runtime: ContainerRuntime,
        session: SessionManager,
    ) -> tuple[list[InfraHealth], list[ServiceHealth], list[StatusIssue]]:
        return _build_dashboard(registry, runtime, session, self._probe)

    def render_dashboard(
        self,
        infra_results: list[InfraHealth],
        service_results: list[ServiceHealth],
        issues: list[StatusIssue],
    ) -> None:
        _render_dashboard(infra_results, service_results, issues)

    def match_panes_to_services(
        self,
        services: list[Service],
        pane_contents: dict[str, str],
    ) -> dict[str, str]:
        return _match_panes_to_services(services, pane_contents)


# ---------------------------------------------------------------------------
# Single-entity checks
# ---------------------------------------------------------------------------

def _check_service(
    registry: Registry, service_name: str, probe: HealthProbe,
) -> ServiceHealth:
    """Check if a single service's port is reachable."""
    svc = registry.get_service(service_name)
    if not svc.port:
        return ServiceHealth(
            name=svc.name, status=ServiceStatus.NO_PORT, port=None, port_open=False,
        )

    host = _resolve_host(svc)
    is_open, tcp_ms = probe.check_port(host, svc.port)

    if not is_open:
        return ServiceHealth(
            name=svc.name, status=ServiceStatus.DOWN, port=svc.port, port_open=False,
        )

    http_ok = False
    response_ms = tcp_ms
    if svc.health_endpoint:
        http_ok, http_ms = probe.check_http(host, svc.port, svc.health_endpoint)
        if http_ms is not None:
            response_ms = http_ms

    status = ServiceStatus.HEALTHY if (http_ok or not svc.health_endpoint) else ServiceStatus.UNHEALTHY
    return ServiceHealth(
        name=svc.name,
        status=status,
        port=svc.port,
        port_open=True,
        http_healthy=http_ok,
        response_time_ms=response_ms,
    )


def _check_infra(
    component: InfraComponent, runtime: ContainerRuntime,
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

def _build_dashboard(
    registry: Registry,
    runtime: ContainerRuntime,
    session: SessionManager,
    probe: HealthProbe,
) -> tuple[list[InfraHealth], list[ServiceHealth], list[StatusIssue]]:
    """Collect health for every component and produce actionable issues."""

    infra_results = [
        _check_infra(comp, runtime)
        for comp in registry.all_infra()
    ]

    pane_contents = session.pane_contents(SESSION_NAME)
    pane_mapping = _match_panes_to_services(registry.all_services(), pane_contents)

    service_results: list[ServiceHealth] = []
    for svc in registry.all_services():
        health = _check_service(registry, svc.name, probe)
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


def _render_dashboard(
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
        if sh.status is ServiceStatus.HEALTHY:
            rt = f"  ({sh.response_time_ms}ms)" if sh.response_time_ms else ""
            print(f"  \u2714 {sh.name:<14}{port_str:<10}healthy{rt}{pane_str}")
        elif sh.status is ServiceStatus.NO_PORT:
            status_label = "worker" if pane_str else "no port"
            print(f"  \u2500 {sh.name:<14}{'':<10}{status_label}{pane_str}")
        elif sh.status is ServiceStatus.UNHEALTHY:
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
# Issue analysis (pure logic — no I/O)
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
        if sh.status in (ServiceStatus.HEALTHY, ServiceStatus.NO_PORT):
            continue
        if sh.name in infra_caused:
            continue
        if sh.status is ServiceStatus.UNHEALTHY:
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
# Helpers (pure logic)
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


def _match_panes_to_services(
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
            if re.search(rf"\b{re.escape(svc_dir)}\b", content) or \
               re.search(rf"\b{re.escape(svc.name)}\b", content):
                mapping[svc.name] = pane_ref
                used_panes.add(pane_ref)
                break
    return mapping
