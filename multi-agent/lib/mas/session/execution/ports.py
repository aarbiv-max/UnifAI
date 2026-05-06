"""
Outbound ports for session execution.

Ports are defined by the use-case owner (session layer) and implemented
by infrastructure adapters (Temporal, Celery, etc.).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from mas.session.domain.workflow_session import WorkflowSession
from mas.core.execution_context import ExecutionContext


@dataclass(frozen=True)
class SubmitSessionRequest:
    """Immutable value object carrying execution context for a background worker.

    Inputs are already staged into the SessionRecord before submission,
    so this only carries the execution context (scope, user, etc.).
    """
    execution_context: ExecutionContext = field(default_factory=ExecutionContext)


class BackgroundSessionSubmitter(ABC):
    """
    Outbound port for fire-and-forget session submission.

    Each adapter (Temporal, Celery, RQ, …) implements this port.
    The adapter is responsible for the full session lifecycle
    (prepare → execute → complete/fail) inside its background worker.

    Returns a handle/ID the caller can use for polling.
    """

    @abstractmethod
    def submit(self, session: WorkflowSession, request: SubmitSessionRequest) -> str:
        """
        Submit the session for background execution.

        Returns:
            A workflow/task handle that the caller can use for status polling.
        """
        ...


# ── File Upload Port ──────────────────────────────────────────────────


class FileUploadError(Exception):
    """Raised when file upload fails after exhausting retries.

    Adapters MUST wrap vendor-specific exceptions into this type.
    The message should be user-presentable.
    """

    def __init__(self, message: str, failed_file: str = "", retriable: bool = False):
        self.failed_file = failed_file
        self.retriable = retriable
        super().__init__(message)


@dataclass(frozen=True)
class FileUploadRequest:
    """Single file to upload — input DTO for the port."""
    file_name: str
    file_bytes: bytes
    mime_type: str


@dataclass(frozen=True)
class FileUploadResult:
    """Successful upload reference — output DTO from the port."""
    file_name: str
    mime_type: str
    file_uri: str
    size_bytes: int


class IFileUploadService(ABC):
    """Outbound port for file upload operations."""

    @abstractmethod
    def upload_batch(self, files: List[FileUploadRequest]) -> List[FileUploadResult]:
        """Upload multiple files atomically.

        Returns results in the same order as the input list.
        If any upload fails, the adapter cleans up already-uploaded
        files and raises FileUploadError.
        """
        ...
