"""Multi-Agent service definition for local development."""

from __future__ import annotations

from pathlib import Path

from core.base_service import BaseService


class MultiAgentService(BaseService):

    @property
    def name(self) -> str:
        return "multi-agent"

    @property
    def directory(self) -> Path:
        return Path("multi-agent")

    @property
    def port(self) -> int | None:
        return int(self._config.multi_agent_port)

    @property
    def required_infrastructure(self) -> list[str]:
        return ["mongo", "redis", "temporal"]

    def venv_build_commands(self, python: str) -> list[list[str]]:
        return [
            [python, "-m", "venv", "venv"],
            ["venv/bin/pip", "install", "-e", ".[all]"],
            ["venv/bin/pip", "install", "-e", "../global_utils"],
        ]

    def run_command(self) -> str:
        d = self.absolute_directory
        return (
            f"cd {d} && source venv/bin/activate"
            f" && HOSTNAME=0.0.0.0 mas api dev"
        )
