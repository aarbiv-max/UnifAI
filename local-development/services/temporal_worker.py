"""Temporal worker service definition for local development."""

from __future__ import annotations

from pathlib import Path

from core.base_service import BaseService


class TemporalWorkerService(BaseService):

    @property
    def name(self) -> str:
        return "temporal-worker"

    @property
    def directory(self) -> Path:
        return Path("multi-agent")

    @property
    def is_primary(self) -> bool:
        return False

    @property
    def required_infrastructure(self) -> list[str]:
        return ["mongo", "redis", "temporal"]

    def run_command(self) -> str:
        d = self.absolute_directory
        return (
            f"cd {d} && source venv/bin/activate"
            f" && mas temporal-worker --threads 20"
        )
