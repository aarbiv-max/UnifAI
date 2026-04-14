"""Concrete service definitions for local development."""

from .backend import BackendService
from .celery_worker import CeleryWorkerService
from .multi_agent import MultiAgentService
from .rag import RagService
from .sso import SsoService
from .temporal_worker import TemporalWorkerService
from .ui import UiService

ALL_SERVICES: list[type] = [
    BackendService,
    RagService,
    MultiAgentService,
    SsoService,
    UiService,
    CeleryWorkerService,
    TemporalWorkerService,
]

__all__ = [
    "ALL_SERVICES",
    "BackendService",
    "CeleryWorkerService",
    "MultiAgentService",
    "RagService",
    "SsoService",
    "TemporalWorkerService",
    "UiService",
]
