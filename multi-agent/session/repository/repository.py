from abc import ABC, abstractmethod
from typing import List, Mapping, Any, Dict
from session.workflow_session import WorkflowSession
from core.dto import GroupedCount


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

    @abstractmethod
    def delete(self, run_id: str) -> bool:
        """Delete a session by run_id. Returns True if deleted, False if not found."""
        ...

    @abstractmethod
    def count(self, user_id: str, filter: Dict[str, Any]) -> int:
        """Count sessions matching filter criteria for a user."""
        ...
    
    @abstractmethod
    def group_count(
        self, 
        user_id: str, 
        group_by: List[str],
        filter: Dict[str, Any] = None
    ) -> List[GroupedCount]:
        """
        Group documents by specified fields and return counts.
        Implementation should perform efficient server-side grouping.
        
        Args:
            user_id: The user ID to filter by
            group_by: List of field names to group by
            filter: Optional additional filter criteria
            
        Returns:
            List of GroupedCount DTOs with grouped field values and count.
            Example: [GroupedCount(fields={"blueprint_id": "bp-123"}, count=10), ...]
        """
        ...

    # ---------- System-wide methods (for admin analytics) ----------

    @abstractmethod
    def count_system(self, filter: Dict[str, Any] = None) -> int:
        """
        Count all sessions system-wide (no user_id constraint).
        
        Args:
            filter: Optional filter criteria
            
        Returns:
            Total count of sessions matching the criteria
        """
        ...

    @abstractmethod
    def get_distinct_users(self, filter: Dict[str, Any] = None) -> List[str]:
        """
        Get distinct user IDs from all sessions.
        
        Args:
            filter: Optional filter criteria
            
        Returns:
            List of distinct user IDs
        """
        ...

    @abstractmethod
    def group_count_system(
        self, 
        group_by: List[str],
        filter: Dict[str, Any] = None
    ) -> List[GroupedCount]:
        """
        Group all sessions by specified fields and return counts (system-wide).
        No user_id constraint - for admin analytics.
        
        Args:
            group_by: List of field names to group by
            filter: Optional filter criteria
            
        Returns:
            List of GroupedCount DTOs with grouped field values and count.
        """
        ...

    @abstractmethod
    def get_time_series(
        self, 
        time_range: str = "all",
        field_path: str = "run_context.started_at"
    ) -> List[Dict[str, Any]]:
        """
        Get time series activity data grouped by appropriate time intervals.
        
        Args:
            time_range: Time filter - "today", "7days", "30days", or "all"
            field_path: Field path for time-based filtering
            
        Returns:
            List of dicts with 'period' (time label) and 'count' (executions)
        """
        ...

    @abstractmethod
    def get_all_stats_faceted(self, time_range: str = "all") -> Dict[str, List[GroupedCount]]:
        """
        Get all stats data using efficient faceted aggregation.
        
        Executes multiple aggregations in parallel for active users,
        top users, and top blueprints data.
        
        Args:
            time_range: Time filter - 'today', '7days', '30days', or 'all'
        
        Returns:
            Dictionary with facet keys containing lists of GroupedCount DTOs.
        """
        ...