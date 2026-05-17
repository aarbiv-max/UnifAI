"""Port: health checking for services and infrastructure."""

from __future__ import annotations

from abc import ABC, abstractmethod

from devtool.domain.models import InfraHealth, ServiceHealth, StatusIssue
from devtool.domain.registry import Registry
from devtool.ports.container_runtime import ContainerRuntime
from devtool.ports.session_manager import SessionManager


class HealthChecker(ABC):

    @abstractmethod
    def check_service(self, registry: Registry, service_name: str) -> ServiceHealth:
        """Check if a single service's port is reachable."""

    @abstractmethod
    def build_dashboard(
        self,
        registry: Registry,
        runtime: ContainerRuntime,
        session: SessionManager,
    ) -> tuple[list[InfraHealth], list[ServiceHealth], list[StatusIssue]]:
        """Collect health for every component and produce actionable issues."""

    @abstractmethod
    def render_dashboard(
        self,
        infra_results: list[InfraHealth],
        service_results: list[ServiceHealth],
        issues: list[StatusIssue],
    ) -> None:
        """Print a human-friendly status dashboard to stdout."""

    @abstractmethod
    def match_panes_to_services(
        self,
        services: list,
        pane_contents: dict[str, str],
    ) -> dict[str, str]:
        """Match services to tmux pane refs by scanning pane content."""
