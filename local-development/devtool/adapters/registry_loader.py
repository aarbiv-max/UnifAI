"""Adapter: loads Registry from a YAML file + environment variables."""

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

from devtool.domain.registry import Registry

_DEFAULT_YAML = Path(__file__).resolve().parent.parent.parent / "services.yaml"


class YamlRegistryLoader:
    """Reads ``services.yaml`` and environment overrides, then builds a
    pure-domain :class:`Registry`."""

    @staticmethod
    def load(yaml_path: Path = _DEFAULT_YAML) -> Registry:
        with open(yaml_path) as fh:
            raw = yaml.safe_load(fh)

        env_val = os.environ.get("UNIFAI_LOCAL_AUTH", "").strip().lower()
        if env_val:
            local_auth = env_val in ("true", "1", "yes")
        else:
            local_auth = bool(raw.get("local_auth", True))

        min_override = (os.environ.get("PYTHON_MIN", "").strip() or None)
        max_override = (os.environ.get("PYTHON_MAX", "").strip() or None)
        python_min, python_max = Registry.parse_python_bounds(
            raw, min_override=min_override, max_override=max_override,
        )

        return Registry(
            services=Registry.parse_services(raw.get("services", {})),
            infra=Registry.parse_infra(raw.get("infrastructure", {})),
            groups=Registry.parse_groups(raw.get("groups", {})),
            local_auth=local_auth,
            python_min=python_min,
            python_max=python_max,
            log_dir=Path(
                raw.get("logging", {}).get("directory", "/tmp/unifai-dev/logs")
            ),
        )
