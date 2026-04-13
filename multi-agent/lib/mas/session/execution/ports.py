"""
Outbound ports for session execution.

Ports are defined by the use-case owner (session layer) and implemented
by infrastructure adapters.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from mas.session.domain.workflow_session import WorkflowSession
from mas.core.execution_context import ExecutionContext


@dataclass(frozen=True)
class SubmitSessionRequest:
    """Immutable value object carrying execution context for a background worker.

    Inputs are already staged into the SessionRecord before submission,
    so this only carries the execution context (scope, user, etc.).
    """
    execution_context: ExecutionContext = field(default_factory=ExecutionContext)


class BackgroundSessionEngine(ABC):
    """
    Outbound port for background workflow operations on a session.

    Each infrastructure adapter (Temporal, Celery, …) implements this port.
    Lifecycle transitions and channel cleanup remain in BackgroundLifecycleHandler —
    this port only handles workflow-level commands.
    """

    @abstractmethod
    def submit(self, session: WorkflowSession, request: SubmitSessionRequest) -> str:
        """Start background execution. Returns a workflow/task handle ID."""
        ...

    @abstractmethod
    def cancel(self, session_id: str, workflow_id: Optional[str] = None) -> None:
        """Request cancellation of a running background session."""
        ...
