from typing import Dict, List, Set, TypedDict, Optional, Any
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from blueprints.service import BlueprintService
from session.service import SessionService
from resources.service import ResourcesService
from core.dto import GroupedCount
from .models import StatisticsResponse, ResourceCategoryStats, OverviewStatisticsResponse, TotalStats


class SessionStats(TypedDict):
    """Internal structure for session statistics."""
    active_count: int
    by_blueprint: Dict[str, int]


class ResourceStats(TypedDict):
    """Internal structure for resource statistics."""
    total: int
    categories_count: int
    by_category: List[ResourceCategoryStats]


class StatisticsService:
    """
    Service for aggregating statistics for all features.
    Centralizes the logic for collecting and formatting workflow, session, and resource statistics.
    
    Architecture:
        - get_all() orchestrates the collection of statistics
        - _get_user_blueprint_ids() handles blueprint domain
        - _get_session_stats() handles session domain with helper _transform_session_counts()
        - _get_resource_stats() handles resource domain with helper _transform_resource_counts()
    """

    def __init__(
        self,
        blueprint_service: BlueprintService,
        session_service: SessionService,
        resources_service: ResourcesService
    ):
        """
        Initialize the StatisticsService.

        Args:
            blueprint_service: Service for blueprint operations
            session_service: Service for session operations
            resources_service: Service for resource operations
        """
        self._blueprint_service = blueprint_service
        self._session_service = session_service
        self._resources_service = resources_service

    def get_all(self, user_id: str) -> StatisticsResponse:
        """
        Get aggregated statistics for all features.
        Returns all stats in a single response for optimal performance.

        This method orchestrates the collection of statistics from different domains,
        delegating to focused helper methods for each area.

        Args:
            user_id: The user ID to get statistics for

        Returns:
            StatisticsResponse: Pydantic model containing all statistics
        """
        # Get blueprint IDs (workflow domain)
        blueprint_ids = self._get_user_blueprint_ids(user_id)
        total_workflows = len(blueprint_ids)
        
        # Get session statistics
        session_stats = self._get_session_stats(user_id, blueprint_ids)
        
        # Get resource statistics
        resource_stats = self._get_resource_stats(user_id)

        return StatisticsResponse(
            totalWorkflows=total_workflows,
            activeSessions=session_stats["active_count"],
            totalResources=resource_stats["total"],
            categoriesInUse=resource_stats["categories_count"],
            blueprintSessionCounts=session_stats["by_blueprint"],
            resourcesByCategory=resource_stats["by_category"]
        )

    def _get_user_blueprint_ids(self, user_id: str) -> Set[str]:
        """
        Get all blueprint IDs belonging to a user.
        
        Args:
            user_id: The user ID to get blueprints for
            
        Returns:
            Set of blueprint IDs owned by the user
        """
        return set(self._blueprint_service.list_ids(user_id=user_id))

    def _get_session_stats(self, user_id: str, valid_blueprint_ids: Set[str]) -> SessionStats:
        """
        Get session statistics for a user.
        
        Args:
            user_id: The user ID to get session stats for
            valid_blueprint_ids: Set of blueprint IDs that the user owns
            
        Returns:
            SessionStats with active_count and by_blueprint counts
        """
        # Get blueprints that have sessions for this user
        blueprints_with_sessions = set(self._session_service.get_user_blueprints(user_id))
        
        # Active = blueprints the user owns AND has sessions for
        active_blueprint_ids = valid_blueprint_ids & blueprints_with_sessions
        active_count = len(active_blueprint_ids)
        
        # Get session counts using group_count() - returns GroupedCount DTOs
        session_counts = self._session_service.group_count(
            user_id, 
            group_by=["blueprint_id"]
        )
        
        # Transform to dict, filtered to user's own blueprints
        by_blueprint = self._transform_session_counts(session_counts, valid_blueprint_ids)
        
        return SessionStats(
            active_count=active_count,
            by_blueprint=by_blueprint
        )

    def _transform_session_counts(
        self, 
        grouped_counts: List[GroupedCount], 
        valid_blueprint_ids: Set[str]
    ) -> Dict[str, int]:
        """
        Transform session GroupedCount results to blueprint->count dict.
        
        Filters results to only include blueprints the user owns.
        
        Args:
            grouped_counts: List of GroupedCount DTOs from session service
            valid_blueprint_ids: Set of blueprint IDs to filter by
            
        Returns:
            Dict mapping blueprint_id to session count
        """
        return {
            item.get("blueprint_id"): item.count
            for item in grouped_counts
            if item.get("blueprint_id") in valid_blueprint_ids
        }

    def _get_resource_stats(self, user_id: str) -> ResourceStats:
        """
        Get resource statistics for a user.
        
        Args:
            user_id: The user ID to get resource stats for
            
        Returns:
            ResourceStats with total, categories_count, and by_category
        """
        # Get resource aggregation using group_count() - returns GroupedCount DTOs
        resources_grouped = self._resources_service.group_count(
            user_id, 
            group_by=["category", "type"]
        )
        
        # Transform to ResourceCategoryStats format
        by_category = self._transform_resource_counts(resources_grouped)
        
        # Get total resources count
        total = self._resources_service.count(user_id)
        
        return ResourceStats(
            total=total,
            categories_count=len(by_category),
            by_category=by_category
        )

    def _transform_resource_counts(
        self, 
        grouped_counts: List[GroupedCount]
    ) -> List[ResourceCategoryStats]:
        """
        Transform resource GroupedCount results to ResourceCategoryStats list.
        
        Groups by category and collects types within each category.
        
        Args:
            grouped_counts: List of GroupedCount DTOs from resource service
            
        Returns:
            List of ResourceCategoryStats with category totals and type breakdowns
        """
        # Group by category and collect types within each category
        category_data: Dict[str, Dict] = {}
        
        for item in grouped_counts:
            category = item.get("category")
            type_name = item.get("type")
            count = item.count
            
            if not category:
                continue
                
            if category not in category_data:
                category_data[category] = {"count": 0, "types": {}}
            
            category_data[category]["count"] += count
            if type_name:
                category_data[category]["types"][type_name] = count
        
        return [
            ResourceCategoryStats(category=cat, count=data["count"], types=data["types"])
            for cat, data in category_data.items()
        ]
    
    def get_overview(self, time_range: str = "all") -> OverviewStatisticsResponse:
        """
        Get comprehensive system-wide overview statistics.
        Returns all key metrics in a single response for the dashboard.
        
        Args:
            time_range: Time filter - 'today', '7days', '30days', or 'all' (default: 'all')
        
        Returns:
            OverviewStatisticsResponse: Pydantic model containing all overview statistics
        """
        # Get total statistics
        total_runs = self._session_service.count_system_wide(time_range=time_range)
        unique_users = len(self._session_service.get_distinct_users(time_range=time_range))
        avg_runs_per_user = round(total_runs / unique_users, 2) if unique_users > 0 else 0
        
        total_stats = TotalStats(
            total_runs=total_runs,
            unique_users=unique_users,
            avg_runs_per_user=avg_runs_per_user
        )
        
        # Get status breakdown
        status_counts = self._session_service.group_count_system_wide(
            group_by=["status"],
            time_range=time_range
        )
        status_breakdown = {
            item.get("status"): item.count
            for item in status_counts
        }
        
        # Get active users
        active_today = self._get_active_users_data(1)
        active_7days = self._get_active_users_data(7)
        active_30days = self._get_active_users_data(30)
        
        # Get top users (all time, limit 10)
        top_users = self._get_top_users(limit=10)
        
        # Get top blueprints (filtered by time_range, limit 10)
        top_blueprints = self._get_top_blueprints(limit=10, time_range=time_range)
        
        # Get time series activity
        time_series = self._session_service.get_time_series_activity(time_range=time_range)
        
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
    
    def _get_active_users_data(self, days: int) -> List[Dict[str, Any]]:
        """
        Get active users for the specified number of days.
        
        Args:
            days: Number of days to look back
        
        Returns:
            List of user activity dicts
        """
        # Map days to time_range
        if days == 1:
            time_range = "today"
        elif days == 7:
            time_range = "7days"
        elif days == 30:
            time_range = "30days"
        else:
            # For custom days, we'll need to use filter directly
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat().replace('+00:00', 'Z')
            user_counts = self._session_service.group_count_system_wide(
                group_by=["user_id", "status"],
                filter={"run_context.started_at": {"$gte": cutoff_iso}}
            )
            return self._process_user_counts(user_counts, days)
        
        # Group by user_id with status breakdown
        user_counts = self._session_service.group_count_system_wide(
            group_by=["user_id", "status"],
            time_range=time_range
        )
        
        return self._process_user_counts(user_counts, days)
    
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
    
    def _process_user_counts(self, user_counts: List[GroupedCount], days: int) -> List[Dict[str, Any]]:
        """
        Process user counts into user activity dicts.
        
        Args:
            user_counts: List of GroupedCount DTOs grouped by user_id and status
            days: Number of days (for field naming)
        
        Returns:
            List of user activity dicts
        """
        user_data = self._aggregate_user_counts(user_counts, run_count_field="recent_runs")
        
        # Sort by recent_runs descending
        result = sorted(user_data.values(), key=lambda x: x["recent_runs"], reverse=True)
        
        # Add days-specific field name
        if days == 1:
            for item in result:
                item["runs_today"] = item.pop("recent_runs")
        
        return result
    
    def _get_top_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top users by total runs (all time).
        
        Args:
            limit: Number of top users to return
        
        Returns:
            List of user activity dicts
        """
        # Group by user_id and status (all time)
        user_counts = self._session_service.group_count_system_wide(
            group_by=["user_id", "status"]
        )
        
        # Aggregate by user
        user_data = self._aggregate_user_counts(user_counts, run_count_field="total_runs")
        
        # Get unique blueprints per user
        blueprint_counts = self._session_service.group_count_system_wide(
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
        blueprint_counts = self._session_service.group_count_system_wide(
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
