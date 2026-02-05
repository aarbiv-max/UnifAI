from typing import Dict, List, Set, TypedDict, Any
from datetime import datetime, timezone
from blueprints.service import BlueprintService
from session.service import SessionService
from resources.service import ResourcesService
from core.dto import GroupedCount
from .models import StatisticsResponse, ResourceCategoryStats, SystemStatsResponse, TotalStats


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

    # ---------- System-wide Stats (for admin dashboard) ----------

    def get_system_stats(self, time_range: str = "all") -> SystemStatsResponse:
        """
        Get system-wide statistics for admin dashboard.
        
        Uses session_service system-wide methods - no parallel repository needed.
        
        Args:
            time_range: Time filter - 'today', '7days', '30days', or 'all' (default: 'all')
        
        Returns:
            SystemStatsResponse containing all system-wide statistics data
        """
        # Calculate total statistics
        total_runs = self._session_service.count_system_with_time_range(time_range)
        distinct_users = self._session_service.get_distinct_users_with_time_range(time_range)
        unique_users = len(distinct_users)
        avg_runs_per_user = round(total_runs / unique_users, 2) if unique_users > 0 else 0
        
        total_stats = TotalStats(
            total_runs=total_runs,
            unique_users=unique_users,
            avg_runs_per_user=avg_runs_per_user
        )
        
        # Get status breakdown
        status_counts = self._session_service.group_count_system_with_time_range(
            group_by=["status"],
            time_range=time_range
        )
        status_breakdown = {
            item.get("status"): item.count
            for item in status_counts
        }
        
        # Get system stats data via faceted query
        faceted_data = self._session_service.get_all_stats_faceted(time_range=time_range)
        
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
        
        # Get time series activity
        time_series = self._session_service.get_time_series(time_range=time_range)
        
        return SystemStatsResponse(
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
