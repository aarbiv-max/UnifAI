"""Registry — loads services.yaml and provides typed lookups."""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "PyYAML is required. Install with: pip install pyyaml",
        file=sys.stderr,
    )
    raise SystemExit(1)

from .models import (
    InfraComponent,
    Service,
    ServiceGroup,
    ServiceType,
    VenvConfig,
    VenvStrategy,
)

_DEFAULT_YAML = Path(__file__).resolve().parent.parent.parent / "services.yaml"


class Registry:
    """Single source of truth built from services.yaml."""

    def __init__(self, yaml_path: Path = _DEFAULT_YAML) -> None:
        with open(yaml_path) as fh:
            raw = yaml.safe_load(fh)

        env_val = os.environ.get("UNIFAI_LOCAL_AUTH", "").strip().lower()
        if env_val:
            self._local_auth = env_val in ("true", "1", "yes")
        else:
            self._local_auth = bool(raw.get("local_auth", True))
        self._python_min, self._python_max = self._parse_python_bounds(raw)
        self._infra = self._parse_infra(raw.get("infrastructure", {}))
        self._services = self._parse_services(raw.get("services", {}))
        self._groups = self._parse_groups(raw.get("groups", {}))
        self._log_dir = Path(
            raw.get("logging", {}).get("directory", "/tmp/unifai-dev/logs")
        )

    # -- public API ----------------------------------------------------------

    def get_service(self, name: str) -> Service:
        if name not in self._services:
            raise KeyError(
                f"Unknown service '{name}'. "
                f"Known services: {', '.join(self._services)}"
            )
        return self._services[name]

    def get_infra(self, name: str) -> InfraComponent:
        if name not in self._infra:
            raise KeyError(
                f"Unknown infrastructure '{name}'. "
                f"Known: {', '.join(self._infra)}"
            )
        return self._infra[name]

    def all_services(self) -> list[Service]:
        return list(self._services.values())

    def all_infra(self) -> list[InfraComponent]:
        return list(self._infra.values())

    def primary_services(self) -> list[Service]:
        seen_dirs: set[Path] = set()
        result: list[Service] = []
        for svc in self._services.values():
            if not svc.is_primary:
                continue
            if svc.directory in seen_dirs:
                continue
            seen_dirs.add(svc.directory)
            result.append(svc)
        return result

    def get_group(self, name: str) -> ServiceGroup:
        if name not in self._groups:
            raise KeyError(
                f"Unknown group '{name}'. "
                f"Known groups: {', '.join(self._groups)}"
            )
        return self._groups[name]

    def service_names(self) -> list[str]:
        return list(self._services.keys())

    def group_names(self) -> list[str]:
        return list(self._groups.keys())

    def infra_names(self) -> list[str]:
        return list(self._infra.keys())

    def groups_for_service(self, name: str) -> list[str]:
        """Return the names of all groups that contain *name*."""
        return [
            g.name for g in self._groups.values()
            if name in g.services
        ]

    def resolve_services(self, targets: list[str]) -> list[Service]:
        """Expand a mix of service names and group names into a
        deduplicated list of Service objects, preserving first-seen order."""
        seen: set[str] = set()
        result: list[Service] = []
        for target in targets:
            if target in self._groups:
                for svc_name in self._groups[target].services:
                    if svc_name not in seen:
                        seen.add(svc_name)
                        result.append(self.get_service(svc_name))
            else:
                if target not in seen:
                    seen.add(target)
                    result.append(self.get_service(target))
        return result

    def infra_for_services(self, services: list[Service]) -> list[InfraComponent]:
        """Union of all infrastructure needed by the given services."""
        seen: set[str] = set()
        result: list[InfraComponent] = []
        for svc in services:
            for name in svc.infrastructure:
                if name not in seen:
                    seen.add(name)
                    result.append(self.get_infra(name))
        return result

    def python_bounds(self) -> tuple[tuple[int, int], tuple[int, int]]:
        return self._python_min, self._python_max

    @property
    def local_auth(self) -> bool:
        return self._local_auth

    @property
    def log_dir(self) -> Path:
        return self._log_dir

    # -- parsing helpers -----------------------------------------------------

    @staticmethod
    def _parse_python_bounds(
        raw: dict,
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        py = raw.get("python", {})
        min_str = os.environ.get("PYTHON_MIN", "").strip() or py.get("min", "3.11")
        max_str = os.environ.get("PYTHON_MAX", "").strip() or py.get("max", "3.13")
        min_parts = min_str.split(".")
        max_parts = max_str.split(".")
        return (
            (int(min_parts[0]), int(min_parts[1])),
            (int(max_parts[0]), int(max_parts[1])),
        )

    @staticmethod
    def _parse_infra(raw: dict) -> dict[str, InfraComponent]:
        result: dict[str, InfraComponent] = {}
        for name, data in raw.items():
            result[name] = InfraComponent(
                name=name,
                image=data["image"],
                ports=data.get("ports", []),
                label=data.get("label", name),
                command=data.get("command"),
                stop_timeout=data.get("stop_timeout"),
            )
        return result

    @staticmethod
    def _parse_services(raw: dict) -> dict[str, Service]:
        result: dict[str, Service] = {}
        for name, data in raw.items():
            venv_raw = data.get("venv", {})
            venv = VenvConfig(
                strategy=VenvStrategy(venv_raw.get("strategy", "none")),
                commands=venv_raw.get("commands", []),
            )
            result[name] = Service(
                name=name,
                directory=Path(data["directory"]),
                port=data.get("port"),
                host=data.get("host"),
                health_endpoint=data.get("health_endpoint"),
                type=ServiceType(data.get("type", "python")),
                infrastructure=data.get("infrastructure", []),
                is_primary=data.get("is_primary", True),
                env_file=data.get("env_file"),
                env_entries=data.get("env_entries", {}),
                venv=venv,
                launch=data["launch"],
            )
        return result

    @staticmethod
    def _parse_groups(raw: dict) -> dict[str, ServiceGroup]:
        return {
            name: ServiceGroup(name=name, services=svc_list)
            for name, svc_list in raw.items()
        }
