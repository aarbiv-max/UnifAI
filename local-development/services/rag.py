"""RAG service definition for local development."""

from __future__ import annotations

from pathlib import Path

from core.base_service import BaseService, PatchSpec


class RagService(BaseService):

    @property
    def name(self) -> str:
        return "rag"

    @property
    def directory(self) -> Path:
        return Path("rag")

    @property
    def port(self) -> int | None:
        return int(self._config.rag_port)

    @property
    def required_infrastructure(self) -> list[str]:
        return ["mongo", "rabbitmq", "qdrant"]

    def env_entries(self) -> dict[str, str] | None:
        return {
            "hostname_local": self._config.rag_host,
            "port": self._config.rag_port,
        }

    @property
    def env_file_path(self) -> Path | None:
        return self._root / "rag" / ".env"

    def patch_specs(self) -> list[PatchSpec]:
        return [
            PatchSpec(
                file=Path("rag/bootstrap/flask_app.py"),
                find="host=config.hostname_local,",
                replace='host="0.0.0.0",',
            ),
        ]

    def run_command(self) -> str:
        d = self.absolute_directory
        return (
            f"cd {d} && source venv/bin/activate"
            f" && set -a && source .env 2>/dev/null; set +a"
            f" && python -m bootstrap.flask_app"
        )
