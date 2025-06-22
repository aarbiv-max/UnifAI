from abc import ABC, abstractmethod
from typing import List, Mapping, Any
from session.workflow_session import WorkflowSession


class SessionRepository(ABC):
    """
    Abstract persistence API for WorkflowSession snapshots.
    """

    @abstractmethod
    def save(self, session: WorkflowSession) -> None:
        """Persist the given session (create or update)."""
        ...

    @abstractmethod
    def fetch(self, run_id: str) -> Mapping[str, Any]:
        """Fetch session raw doc"""
        ...

    @abstractmethod
    def list_runs(self, user_id: str) -> List[str]:
        """Return all run_ids for the given user."""
        ...
