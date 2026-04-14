"""UI (Vite) service definition for local development."""

from __future__ import annotations

import shutil
from pathlib import Path

from core.base_service import BaseService


class UiService(BaseService):

    @property
    def name(self) -> str:
        return "ui"

    @property
    def directory(self) -> Path:
        return Path("ui")

    @property
    def port(self) -> int | None:
        return int(self._config.ui_port)

    def venv_build_commands(self, python: str) -> list[list[str]]:
        if shutil.which("pnpm"):
            return [["pnpm", "install"]]
        if shutil.which("npm"):
            return [["npm", "install"]]
        return []

    @property
    def venv_success_message(self) -> str:
        return f"All packages for {self.name} installed successfully."

    def env_entries(self) -> dict[str, str] | None:
        return {
            "DEV_PORT": self._config.ui_port,
            "DEV_HOST": self._config.ui_host,
            "RAG_HOST": f"http://{self._config.rag_host}:{self._config.rag_port}",
            "MULTIAGENT_HOST": f"http://{self._config.multi_agent_host}:{self._config.multi_agent_port}",
            "SSO_HOST": f"http://{self._config.sso_host}:{self._config.sso_port}",
            "BACKEND_HOST": f"http://{self._config.backend_host}:{self._config.backend_port}",
        }

    @property
    def env_file_path(self) -> Path | None:
        return self._root / "ui" / ".env.local"

    def run_command(self) -> str:
        d = self.absolute_directory
        return (
            f"cd {d} && set -a"
            f" && source .env.local 2>/dev/null; set +a"
            f" && npm start"
        )
