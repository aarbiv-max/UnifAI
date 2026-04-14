"""Celery worker service definition for local development."""

from __future__ import annotations

from pathlib import Path

from core.base_service import BaseService


class CeleryWorkerService(BaseService):

    @property
    def name(self) -> str:
        return "celery-worker"

    @property
    def directory(self) -> Path:
        return Path("rag")

    @property
    def is_primary(self) -> bool:
        return False

    @property
    def required_infrastructure(self) -> list[str]:
        return ["mongo", "rabbitmq", "qdrant"]

    def run_command(self) -> str:
        d = self.absolute_directory
        return (
            f"cd {d} && source venv/bin/activate"
            f" && set -a && source .env 2>/dev/null; set +a"
            f" && celery -A infrastructure.celery.app worker"
            f" -Q document_queue,slack_queue -l info"
        )
