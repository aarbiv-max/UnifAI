"""Backend service definition for local development."""

from __future__ import annotations

from pathlib import Path

from core.base_service import BaseService, PatchSpec


class BackendService(BaseService):

    @property
    def name(self) -> str:
        return "backend"

    @property
    def directory(self) -> Path:
        return Path("backend")

    @property
    def port(self) -> int | None:
        return int(self._config.backend_port)

    @property
    def required_infrastructure(self) -> list[str]:
        return ["mongo"]

    def patch_specs(self) -> list[PatchSpec]:
        return [
            PatchSpec(
                file=Path("backend/run/dev.py"),
                find="app.run(host=config.hostname_local, port=config.port, debug=True)",
                replace='app.run("0.0.0.0", port=config.port, debug=True)',
            ),
        ]

    def run_command(self) -> str:
        d = self.absolute_directory
        return (
            f"cd {d} && source venv/bin/activate"
            f" && set -a && source .env 2>/dev/null; set +a"
            f" && python -m run.dev"
        )
