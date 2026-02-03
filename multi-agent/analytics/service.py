"""
Analytics service for system-wide workflow statistics.

This service provides comprehensive analytics for the admin dashboard,
following the ShareService pattern with dedicated repository.
"""
from typing import Dict, List, Any
from datetime import datetime, timezone

from blueprints.service import BlueprintService
from core.dto import GroupedCount
from .models import OverviewStatisticsResponse, TotalStats
from .repository.base import AnalyticsRepository


class AnalyticsService:
    """
    Service for system-wide analytics statistics.
    
    Provides comprehensive workflow analytics for the admin dashboard:
    - Total runs, unique users, average runs per user
    - Status breakdown (COMPLETED, FAILED, RUNNING, etc.)
    - Active users by time period (today, 7 days, 30 days)
    - Top users by total runs
    - Top blueprints by usage
    - Time series activity data
    
    Architecture:
        - Uses AnalyticsRepository for data access (separation of concerns)
        - Uses BlueprintService only for blueprint name lookups
        - No caching - queries are executed directly (read-only, simple)
    """

    def __init__(
        self,
        analytics_repo: AnalyticsRepository,
        blueprint_service: BlueprintService
    ):
        """
        Initialize the AnalyticsService.

        Args:
            analytics_repo: Repository for analytics data access
            blueprint_service: Service for blueprint name lookups
        """
        self._repo = analytics_repo
        self._blueprint_service = blueprint_service

    def get_analytics(self, time_range: str = "all") -> OverviewStatisticsResponse:
        """
        Get comprehensive system-wide analytics statistics.
        
        Returns all key metrics in a single response for the Analytics dashboard.
        
        Uses optimized $facet query to fetch active users data for all time periods
        (today, 7 days, 30 days) in a single MongoDB round-trip.
        
        Args:
            time_range: Time filter - 'today', '7days', '30days', or 'all' (default: 'all')
        
        Returns:
            OverviewStatisticsResponse: Pydantic model containing all analytics statistics
        """
        # Calculate total statistics
        total_runs = self._repo.count_runs(time_range=time_range)
        unique_users = len(self._repo.get_distinct_users(time_range=time_range))
        avg_runs_per_user = round(total_runs / unique_users, 2) if unique_users > 0 else 0
        
        total_stats = TotalStats(
            total_runs=total_runs,
            unique_users=unique_users,
            avg_runs_per_user=avg_runs_per_user
        )
        
        # Get status breakdown
        status_counts = self._repo.group_by(
            group_by=["status"],
            time_range=time_range
        )
        status_breakdown = {
            item.get("status"): item.count
            for item in status_counts
        }
        
        # Get active users for all time periods in a single optimized query
        faceted_data = self._repo.get_active_users_faceted()
        
        active_today = self._process_faceted_user_data(
            faceted_data["today_status"],
            faceted_data["today_blueprints"],
            days=1
        )
        active_7days = self._process_faceted_user_data(
            faceted_data["week_status"],
            faceted_data["week_blueprints"],
            days=7
        )
        active_30days = self._process_faceted_user_data(
            faceted_data["month_status"],
            faceted_data["month_blueprints"],
            days=30
        )
        
        # Get top users (all time, limit 10)
        top_users = self._get_top_users(limit=10)
        
        # Get top blueprints (filtered by time_range, limit 10)
        top_blueprints = self._get_top_blueprints(limit=10, time_range=time_range)
        
        # Get time series activity
        time_series = self._repo.get_time_series(time_range=time_range)
        
        return OverviewStatisticsResponse(
            total_stats=total_stats,
            status_breakdown=status_breakdown,
            active_today=active_today,
            active_7days=active_7days,
            active_30days=active_30days,
            top_users=top_users,
            top_blueprints=top_blueprints,
            time_series=time_series,
            generated_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        )

    def _process_faceted_user_data(
        self,
        status_counts: List[GroupedCount],
        blueprint_counts: List[GroupedCount],
        days: int
    ) -> List[Dict[str, Any]]:
        """
        Process pre-fetched faceted data into user activity dicts.
        
        This method works with data already fetched by get_active_users_faceted(),
        avoiding additional database queries.
        
        Args:
            status_counts: User+status groupings from faceted query
            blueprint_counts: User+blueprint groupings from faceted query
            days: Number of days (for field naming)
        
        Returns:
            List of user activity dicts sorted by run count
        """
        # Aggregate by user from status counts
        user_data = self._aggregate_user_counts(status_counts, run_count_field="recent_runs")
        
        # Add unique blueprint counts from blueprint data
        for item in blueprint_counts:
            user_id = item.get("user_id")
            if user_id in user_data:
                if "unique_blueprints" not in user_data[user_id]:
                    user_data[user_id]["unique_blueprints"] = set()
                user_data[user_id]["unique_blueprints"].add(item.get("blueprint_id"))
        
        # Convert sets to counts
        for user_id in user_data:
            if "unique_blueprints" in user_data[user_id]:
                user_data[user_id]["unique_blueprints"] = len(user_data[user_id]["unique_blueprints"])
            else:
                user_data[user_id]["unique_blueprints"] = 0
        
        # Sort by recent_runs descending
        result = sorted(user_data.values(), key=lambda x: x["recent_runs"], reverse=True)
        
        # Add days-specific field name for "today"
        if days == 1:
            for item in result:
                item["runs_today"] = item.pop("recent_runs")
        
        return result

    def _aggregate_user_counts(
        self,
        user_counts: List[GroupedCount],
        run_count_field: str = "recent_runs"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate user counts by user_id and status.
        
        Args:
            user_counts: List of GroupedCount DTOs grouped by user_id and status
            run_count_field: Field name for the run count (e.g., "recent_runs", "total_runs")
        
        Returns:
            Dictionary mapping user_id to user data dict
        """
        user_data: Dict[str, Dict] = {}
        for item in user_counts:
            user_id = item.get("user_id")
            status = item.get("status")
            count = item.count
            
            if user_id not in user_data:
                user_data[user_id] = {
                    "user_id": user_id,
                    run_count_field: 0,
                    "status_breakdown": {}
                }
            
            user_data[user_id][run_count_field] += count
            if status:
                if status not in user_data[user_id]["status_breakdown"]:
                    user_data[user_id]["status_breakdown"][status] = 0
                user_data[user_id]["status_breakdown"][status] += count
        
        return user_data


    def _get_top_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top users by total runs (all time).
        
        Args:
            limit: Number of top users to return
        
        Returns:
            List of user activity dicts
        """
        # Group by user_id and status (all time)
        user_counts = self._repo.group_by(
            group_by=["user_id", "status"]
        )
        
        # Aggregate by user
        user_data = self._aggregate_user_counts(user_counts, run_count_field="total_runs")
        
        # Get unique blueprints per user
        blueprint_counts = self._repo.group_by(
            group_by=["user_id", "blueprint_id"]
        )
        for item in blueprint_counts:
            user_id = item.get("user_id")
            if user_id in user_data:
                if "unique_blueprints" not in user_data[user_id]:
                    user_data[user_id]["unique_blueprints"] = set()
                user_data[user_id]["unique_blueprints"].add(item.get("blueprint_id"))
        
        # Convert sets to counts
        for user_id in user_data:
            if "unique_blueprints" in user_data[user_id]:
                user_data[user_id]["unique_blueprints"] = len(user_data[user_id]["unique_blueprints"])
            else:
                user_data[user_id]["unique_blueprints"] = 0
        
        # Sort by total_runs descending and limit
        result = sorted(user_data.values(), key=lambda x: x["total_runs"], reverse=True)[:limit]
        return result

    def _get_blueprint_name(self, blueprint_id: str) -> str:
        """
        Get blueprint display name, falling back to blueprint_id if not found.
        
        Args:
            blueprint_id: The blueprint ID to look up
        
        Returns:
            Blueprint name or blueprint_id if not found
        """
        try:
            if self._blueprint_service.exists(blueprint_id):
                bp_doc = self._blueprint_service.get_blueprint_draft_doc(blueprint_id)
                spec_dict = bp_doc.get("spec_dict", {})
                if isinstance(spec_dict, dict):
                    return spec_dict.get("name", blueprint_id)
        except Exception:
            pass
        
        return blueprint_id

    def _get_top_blueprints(self, limit: int = 10, time_range: str = "all") -> List[Dict[str, Any]]:
        """
        Get most used blueprints.
        
        Args:
            limit: Number of top blueprints to return
            time_range: Time filter - 'today', '7days', '30days', or 'all'
        
        Returns:
            List of blueprint usage dicts
        """
        # Group by blueprint_id and user_id
        blueprint_counts = self._repo.group_by(
            group_by=["blueprint_id", "user_id"],
            time_range=time_range
        )
        
        # Aggregate by blueprint
        blueprint_data: Dict[str, Dict] = {}
        for item in blueprint_counts:
            blueprint_id = item.get("blueprint_id")
            user_id = item.get("user_id")
            count = item.count
            
            if blueprint_id not in blueprint_data:
                blueprint_data[blueprint_id] = {
                    "blueprint_id": blueprint_id,
                    "run_count": 0,
                    "unique_users": set()
                }
            
            blueprint_data[blueprint_id]["run_count"] += count
            if user_id:
                blueprint_data[blueprint_id]["unique_users"].add(user_id)
        
        # Convert sets to counts and get blueprint names
        result = []
        for blueprint_id, data in blueprint_data.items():
            data["unique_users"] = len(data["unique_users"])
            data["blueprint_name"] = self._get_blueprint_name(blueprint_id)
            result.append(data)
        
        # Sort by run_count descending and limit
        result = sorted(result, key=lambda x: x["run_count"], reverse=True)[:limit]
        return result
