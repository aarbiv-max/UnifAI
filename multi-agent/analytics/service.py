"""
Analytics service for system-wide workflow statistics.

This service provides comprehensive analytics for the admin dashboard,
following the ShareService pattern with dedicated repository.
"""
from typing import Dict, List, Any, Set
from datetime import datetime, timezone

from blueprints.service import BlueprintService
from core.dto import GroupedCount
from .models import OverviewStatisticsResponse, TotalStats
from .repository.base import AnalyticsRepository


class AnalyticsService:
    """
    Service for system-wide analytics statistics.
    
    Provides workflow analytics for the admin dashboard:
    - Total runs, unique users, average runs per user
    - Status breakdown (COMPLETED, FAILED, RUNNING, etc.)
    - Active users by time period (today, 7 days, 30 days)
    - Top users by total runs
    - Top blueprints by usage
    - Time series activity data
    
    Architecture:
        - Uses AnalyticsRepository for data access (separation of concerns)
        - Uses BlueprintService for blueprint name lookups
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
        Get system-wide analytics statistics.
        
        Args:
            time_range: Time filter - 'today', '7days', '30days', or 'all' (default: 'all')
        
        Returns:
            OverviewStatisticsResponse containing all analytics data
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
        
        # Get analytics data via faceted query
        faceted_data = self._repo.get_all_analytics_faceted(time_range=time_range)
        
        # Process active users from faceted data
        active_today = self._process_user_data(
            faceted_data["today_status"],
            faceted_data["today_blueprints"],
            run_count_field="runs_today"
        )
        active_7days = self._process_user_data(
            faceted_data["week_status"],
            faceted_data["week_blueprints"],
            run_count_field="recent_runs"
        )
        active_30days = self._process_user_data(
            faceted_data["month_status"],
            faceted_data["month_blueprints"],
            run_count_field="recent_runs"
        )
        
        # Process top users from faceted data
        top_users = self._process_user_data(
            faceted_data["top_users_status"],
            faceted_data["top_users_blueprints"],
            run_count_field="total_runs",
            limit=10
        )
        
        # Process top blueprints from faceted data
        top_blueprints = self._process_blueprint_data(
            faceted_data["top_blueprints_data"],
            limit=10
        )
        
        # Get time series activity (separate query - different structure)
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

    def _process_user_data(
        self,
        status_counts: List[GroupedCount],
        blueprint_counts: List[GroupedCount],
        run_count_field: str = "recent_runs",
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Process user data from faceted query results.
        
        Combines status counts and blueprint counts into user activity dicts.
        This is a reusable helper that works for active users and top users.
        
        Args:
            status_counts: User+status groupings from faceted query
            blueprint_counts: User+blueprint groupings from faceted query
            run_count_field: Field name for run count (e.g., "recent_runs", "total_runs")
            limit: Optional limit on number of results
        
        Returns:
            List of user activity dicts sorted by run count
        """
        # Aggregate by user from status counts
        user_data = self._aggregate_user_counts(status_counts, run_count_field=run_count_field)
        
        # Add unique blueprint counts
        self._add_blueprint_counts(user_data, blueprint_counts)
        
        # Sort by run count descending
        result = sorted(user_data.values(), key=lambda x: x[run_count_field], reverse=True)
        
        # Apply limit if specified
        if limit:
            result = result[:limit]
        
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
            run_count_field: Field name for the run count
        
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

    def _add_blueprint_counts(
        self,
        user_data: Dict[str, Dict[str, Any]],
        blueprint_counts: List[GroupedCount]
    ) -> None:
        """
        Add unique blueprint counts to user data dict (in-place).
        
        Args:
            user_data: Dictionary mapping user_id to user data (modified in place)
            blueprint_counts: User+blueprint groupings from faceted query
        """
        # Collect unique blueprints per user
        user_blueprints: Dict[str, Set[str]] = {}
        for item in blueprint_counts:
            user_id = item.get("user_id")
            blueprint_id = item.get("blueprint_id")
            if user_id:
                if user_id not in user_blueprints:
                    user_blueprints[user_id] = set()
                if blueprint_id:
                    user_blueprints[user_id].add(blueprint_id)
        
        # Add counts to user_data
        for user_id in user_data:
            user_data[user_id]["unique_blueprints"] = len(user_blueprints.get(user_id, set()))

    def _process_blueprint_data(
        self,
        blueprint_counts: List[GroupedCount],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Process blueprint data from faceted query results.
        
        Args:
            blueprint_counts: Blueprint+user groupings from faceted query
            limit: Maximum number of blueprints to return
        
        Returns:
            List of blueprint usage dicts with names
        """
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
        
        # Sort by run_count to get top blueprints first
        sorted_blueprints = sorted(
            blueprint_data.items(),
            key=lambda x: x[1]["run_count"],
            reverse=True
        )[:limit]
        
        # Batch lookup blueprint names (only for top N)
        blueprint_ids = [bp_id for bp_id, _ in sorted_blueprints]
        blueprint_names = self._batch_get_blueprint_names(blueprint_ids)
        
        # Build result
        result = []
        for blueprint_id, data in sorted_blueprints:
            result.append({
                "blueprint_id": blueprint_id,
                "blueprint_name": blueprint_names.get(blueprint_id, blueprint_id),
                "run_count": data["run_count"],
                "unique_users": len(data["unique_users"])
            })
        
        return result

    def _batch_get_blueprint_names(self, blueprint_ids: List[str]) -> Dict[str, str]:
        """
        Get blueprint names for multiple blueprints in batch.
        
        Args:
            blueprint_ids: List of blueprint IDs to look up
        
        Returns:
            Dictionary mapping blueprint_id to blueprint_name
        """
        names = {}
        for blueprint_id in blueprint_ids:
            try:
                if self._blueprint_service.exists(blueprint_id):
                    bp_doc = self._blueprint_service.get_blueprint_draft_doc(blueprint_id)
                    spec_dict = bp_doc.get("spec_dict", {})
                    if isinstance(spec_dict, dict):
                        names[blueprint_id] = spec_dict.get("name", blueprint_id)
                    else:
                        names[blueprint_id] = blueprint_id
                else:
                    names[blueprint_id] = blueprint_id
            except Exception:
                names[blueprint_id] = blueprint_id
        
        return names
