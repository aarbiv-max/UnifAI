from typing import List, Mapping, Any, Dict, Optional
from session.repository.repository import SessionRepository
from session.workflow_session_factory import WorkflowSessionFactory
from session.workflow_session import WorkflowSession
from core.run_context import RunContext
from core.dto import GroupedCount
from graph.state.graph_state import GraphState
from session.status import SessionStatus
from blueprints.service import BlueprintService
from session.models import SessionMeta
from .exceptions import BlueprintNotFoundError


class UserSessionManager:
    """
    High‐level CRUD for user sessions.
    SRP: only creates, loads, and lists run_ids.
    """

    def __init__(
            self,
            repository: SessionRepository,
            session_factory: WorkflowSessionFactory,
            blueprint_service: BlueprintService
    ):
        self._repo = repository
        self._factory = session_factory
        self._bp_service = blueprint_service

    def blueprint_exists(self, blueprint_id: str) -> bool:
        """Check if blueprint exists without loading it."""
        return self._bp_service.exists(blueprint_id)

    def create_session(
            self,
            user_id: str,
            blueprint_id: str,
            metadata: SessionMeta = None
    ) -> WorkflowSession:
        """Instantiate a fresh session and persist it. Returns run_id."""
        
        # Check if blueprint exists before proceeding
        if not self.blueprint_exists(blueprint_id):
            raise BlueprintNotFoundError(blueprint_id)
        
        session = self._factory.create(
            blueprint_spec=self._bp_service.load_resolved(blueprint_id),
            blueprint_id=blueprint_id,
            user_id=user_id,
            metadata=metadata
        )

        self._repo.save(session)
        return session

    def get_doc(self, run_id: str) -> Mapping[str, Any]:
        return self._repo.fetch(run_id)

    def get_session(self, run_id: str) -> WorkflowSession:
        """Retrieve a previously created session."""
        doc = self.get_doc(run_id)
        blueprint_id = doc.get("blueprint_id")

        # Check if blueprint exists before proceeding
        if not self.blueprint_exists(blueprint_id):
            raise BlueprintNotFoundError(blueprint_id, session_id=run_id)

        # Rehydrate RunContext
        ctx = RunContext.from_dict(doc["run_context"])

        # Re-create fresh session via factory
        session = self._factory.create(
            user_id=ctx.user_id,
            blueprint_spec=self._bp_service.load_resolved(blueprint_id),
            blueprint_id=blueprint_id,
            metadata=SessionMeta.from_dict(doc.get("metadata", {}))
        )

        # Override run_context (so we keep the same run_id, timestamps)
        session.run_context = ctx

        # Override session status
        status_str = doc.get("status", SessionStatus.PENDING.name)
        session.status = SessionStatus[status_str]

        # Restore GraphState in one shot
        session.graph_state = GraphState(**doc["graph_state"])

        return session

    def list_sessions_ids(self, user_id: str) -> List[str]:
        """All run_ids belonging to this user."""
        return self._repo.list_runs(user_id)

    def list_docs(self, user_id: str) -> List[Mapping[str, Any]]:
        session_ids = self.list_sessions_ids(user_id)
        return [self.get_doc(session_id) for session_id in session_ids]

    def delete_session(self, run_id: str) -> bool:
        """Delete a session by run_id. Returns True if deleted, False if not found."""
        return self._repo.delete(run_id)

    # ---------- statistics ----------
    def count(self, user_id: str, filter: Dict[str, Any] = None) -> int:
        """Count sessions matching filter criteria for a user."""
        return self._repo.count(user_id, filter or {})

    def group_count(
        self, 
        user_id: str, 
        group_by: List[str],
        filter: Dict[str, Any] = None
    ) -> List[GroupedCount]:
        """
        Group sessions by specified fields and return counts.
        Performs efficient server-side grouping via the repository.
        
        Args:
            user_id: The user ID to filter by
            group_by: List of field names to group by (e.g., ["blueprint_id"])
            filter: Optional additional filter criteria
            
        Returns:
            List of GroupedCount DTOs with grouped field values and count.
        """
        return self._repo.group_count(user_id, group_by, filter)
    
    # ---------- system-wide statistics ----------
    def group_count_system_wide(
        self,
        group_by: List[str],
        filter: Dict[str, Any] = None,
        time_range: Optional[str] = None
    ) -> List[GroupedCount]:
        """
        Group sessions by specified fields across all users (system-wide).
        Supports time-based filtering via time_range parameter.
        
        Args:
            group_by: List of field names to group by (e.g., ["blueprint_id", "status"])
            filter: Optional additional filter criteria
            time_range: Optional time filter - "today", "7days", "30days", or "all"
            
        Returns:
            List of GroupedCount DTOs with grouped field values and count.
        """
        # Check if repository supports system-wide queries
        if hasattr(self._repo, 'group_count_system_wide'):
            return self._repo.group_count_system_wide(group_by, filter, time_range)
        else:
            raise NotImplementedError("Repository does not support system-wide queries")
    
    def count_system_wide(
        self,
        filter: Dict[str, Any] = None,
        time_range: Optional[str] = None
    ) -> int:
        """
        Count sessions across all users (system-wide).
        Supports time-based filtering via time_range parameter.
        
        Args:
            filter: Optional additional filter criteria
            time_range: Optional time filter - "today", "7days", "30days", or "all"
            
        Returns:
            Total count of sessions matching the criteria
        """
        if hasattr(self._repo, 'count_system_wide'):
            return self._repo.count_system_wide(filter, time_range)
        else:
            raise NotImplementedError("Repository does not support system-wide queries")
    
    def get_distinct_users(
        self,
        filter: Dict[str, Any] = None,
        time_range: Optional[str] = None
    ) -> List[str]:
        """
        Get distinct user IDs across all sessions (system-wide).
        Supports time-based filtering via time_range parameter.
        
        Args:
            filter: Optional additional filter criteria
            time_range: Optional time filter - "today", "7days", "30days", or "all"
            
        Returns:
            List of distinct user IDs
        """
        if hasattr(self._repo, 'get_distinct_users'):
            return self._repo.get_distinct_users(filter, time_range)
        else:
            raise NotImplementedError("Repository does not support system-wide queries")
    
    def get_time_series_activity(
        self,
        time_range: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Get time series activity data grouped by appropriate time intervals.
        
        Args:
            time_range: 'today', '7days', '30days', or 'all'
        
        Returns:
            List of dicts with 'period' (time label) and 'count' (workflow executions)
        """
        if hasattr(self._repo, 'get_time_series_activity'):
            return self._repo.get_time_series_activity(time_range)
        else:
            raise NotImplementedError("Repository does not support time series queries")