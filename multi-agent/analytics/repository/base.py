"""
Abstract base class for analytics repositories.

Defines the interface for analytics data access, following the ShareRepository pattern.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from core.dto import GroupedCount


class AnalyticsRepository(ABC):
    """
    Abstract repository for analytics operations.
    
    Provides system-wide query capabilities for workflow analytics.
    Implementations handle database-specific logic.
    """

    @abstractmethod
    def count_runs(self, filter: Dict[str, Any] = None, time_range: str = "all") -> int:
        """
        Count workflow runs across all users.
        
        Args:
            filter: Optional additional filter criteria
            time_range: Time filter - "today", "7days", "30days", or "all"
            
        Returns:
            Total count of runs matching the criteria
        """
        pass

    @abstractmethod
    def get_distinct_users(self, filter: Dict[str, Any] = None, time_range: str = "all") -> List[str]:
        """
        Get distinct user IDs who have run workflows.
        
        Args:
            filter: Optional additional filter criteria
            time_range: Time filter - "today", "7days", "30days", or "all"
            
        Returns:
            List of distinct user IDs
        """
        pass

    @abstractmethod
    def group_by(
        self, 
        group_by: List[str], 
        filter: Dict[str, Any] = None, 
        time_range: str = "all"
    ) -> List[GroupedCount]:
        """
        Group workflow runs by specified fields and return counts.
        
        Args:
            group_by: List of field names to group by (e.g., ["status"], ["user_id", "blueprint_id"])
            filter: Optional additional filter criteria
            time_range: Time filter - "today", "7days", "30days", or "all"
            
        Returns:
            List of GroupedCount DTOs with grouped field values and count
        """
        pass

    @abstractmethod
    def get_time_series(self, time_range: str = "all") -> List[Dict[str, Any]]:
        """
        Get time series activity data grouped by appropriate time intervals.
        
        Args:
            time_range: Time filter - "today", "7days", "30days", or "all"
            
        Returns:
            List of dicts with 'period' (time label) and 'count' (workflow executions)
        """
        pass

    @abstractmethod
    def get_all_analytics_faceted(self, time_range: str = "all") -> Dict[str, List[GroupedCount]]:
        """
        Get all analytics data using MongoDB $facet aggregation.
        
        Executes multiple aggregations in parallel:
        - Active users data (today, 7 days, 30 days) with status and blueprint groupings
        - All-time user data for top users
        - Blueprint data for top blueprints (filtered by time_range)
        
        Args:
            time_range: Time filter for top_blueprints - 'today', '7days', '30days', or 'all'
        
        Returns:
            Dictionary with keys for each facet, containing lists of GroupedCount DTOs.
        """
        pass
