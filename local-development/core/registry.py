"""Service registry — collects all service definitions and provides lookup."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.local_dev_config import LocalDevConfig

from .base_service import BaseService


class ServiceRegistry:
    """Instantiates every registered service class and provides lookup helpers."""

    def __init__(self, root: Path, config: LocalDevConfig, service_classes: list[type[BaseService]]) -> None:
        self._services: dict[str, BaseService] = {}
        for cls in service_classes:
            instance = cls(root, config)
            self._services[instance.name] = instance

    def get(self, name: str) -> BaseService:
        """Look up a service by CLI name.Raises KeyError if the name is not registered."""
        if name not in self._services:
            raise KeyError(
                f"Unknown service '{name}'. "
                f"Known services: {', '.join(self._services)}"
            )
        return self._services[name]

    def all(self) -> list[BaseService]:
        """All registered services in registration order."""
        return list(self._services.values())

    def primary_services(self) -> list[BaseService]:
        """Services that own their venv (deduplicates shared directories)."""
        seen_dirs: set[Path] = set()
        result: list[BaseService] = []
        for svc in self._services.values():
            if not svc.is_primary:
                continue
            if svc.directory in seen_dirs:
                continue
            seen_dirs.add(svc.directory)
            result.append(svc)
        return result
