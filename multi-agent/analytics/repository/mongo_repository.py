"""
MongoDB implementation of the AnalyticsRepository.

Provides analytics queries against the workflow_sessions collection.
"""
import pymongo
from pymongo.collection import Collection
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from .base import AnalyticsRepository
from core.dto import GroupedCount
from analytics import utils as analytics_utils
import logging

logger = logging.getLogger(__name__)

class MongoAnalyticsRepository(AnalyticsRepository):
    """
    MongoDB implementation for analytics operations.
    
    Queries the workflow_sessions collection for system-wide analytics.
    """

    def __init__(
        self,
        mongodb_port: str = "27017",
        mongodb_ip: str = "localhost",
        db_name: str = "UnifAI",
        collection_name: str = "workflow_sessions",
    ):
        """
        Initialize MongoDB connection for analytics.
        
        Args:
            mongodb_port: MongoDB port
            mongodb_ip: MongoDB host IP
            db_name: Database name
            collection_name: Collection name (typically workflow_sessions)
        """
        mongo_uri = f"mongodb://{mongodb_ip}:{mongodb_port}/"
        client = pymongo.MongoClient(mongo_uri)
        db = client[db_name]
        self._col: Collection = db[collection_name]
        
        # Ensure indexes exist for analytics queries
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create indexes for optimized analytics queries."""
        # Time-based queries
        self._col.create_index([("run_context.started_at", pymongo.ASCENDING)])
        # Status aggregation
        self._col.create_index([("status", pymongo.ASCENDING)])
        # Blueprint aggregation
        self._col.create_index([("blueprint_id", pymongo.ASCENDING)])
        # User activity queries
        self._col.create_index([
            ("user_id", pymongo.ASCENDING),
            ("run_context.started_at", pymongo.ASCENDING)
        ])

    def _apply_time_range_filter(
        self, 
        filter_dict: Optional[Dict[str, Any]], 
        time_range: Optional[str]
    ) -> Dict[str, Any]:
        """
        Apply time range filtering to a filter dictionary.
        
        Args:
            filter_dict: Base filter dictionary
            time_range: Optional time filter - "today", "7days", "30days", or "all"
            
        Returns:
            Filter dictionary with time range applied if specified
        """
        return analytics_utils.apply_time_range_filter(filter_dict or {}, time_range)

    def count_runs(self, filter: Dict[str, Any] = None, time_range: str = "all") -> int:
        """
        Count workflow runs across all users.
        
        Args:
            filter: Optional additional filter criteria
            time_range: Time filter - "today", "7days", "30days", or "all"
            
        Returns:
            Total count of runs matching the criteria
        """
        query = self._apply_time_range_filter(filter, time_range)
        return self._col.count_documents(query)

    def get_distinct_users(self, filter: Dict[str, Any] = None, time_range: str = "all") -> List[str]:
        """
        Get distinct user IDs who have run workflows.
        
        Args:
            filter: Optional additional filter criteria
            time_range: Time filter - "today", "7days", "30days", or "all"
            
        Returns:
            List of distinct user IDs
        """
        match = self._apply_time_range_filter(filter, time_range)
        return self._col.distinct("user_id", match)

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
        match = self._apply_time_range_filter(filter, time_range)
        group_id = {field: f"${field}" for field in group_by}
        
        pipeline = [
            {"$match": match},
            {"$group": {"_id": group_id, "count": {"$sum": 1}}}
        ]
        
        # Transform MongoDB format → clean DTO
        return [
            GroupedCount(fields=doc["_id"], count=doc["count"])
            for doc in self._col.aggregate(pipeline)
        ]

    def get_time_series(self, time_range: str = "all") -> List[Dict[str, Any]]:
        """
        Get time series activity data grouped by appropriate time intervals.
        
        Args:
            time_range: Time filter - "today", "7days", "30days", or "all"
            
        Returns:
            List of dicts with 'period' (time label) and 'count' (workflow executions)
        """
        now = datetime.now(timezone.utc)
        cutoff_date, date_format = analytics_utils.get_time_range_params(time_range, now)
        cutoff_iso = cutoff_date.isoformat().replace('+00:00', 'Z') if cutoff_date else None
        
        pipeline = analytics_utils.build_time_series_pipeline(cutoff_iso, date_format)
        
        try:
            results = list(self._col.aggregate(pipeline))
            return [{"period": doc["_id"], "count": doc["count"]} for doc in results]
        except Exception as e:
            logger.warning(f"Failed to get time series data: {e}")
            return []

    def get_all_analytics_faceted(self, time_range: str = "all") -> Dict[str, List[GroupedCount]]:
        """
        Get all analytics data using MongoDB $facet aggregation.
        
        Executes multiple aggregations in parallel:
        - Active users data (today, 7 days, 30 days) with status and blueprint groupings
        - Top users data (filtered by time_range, or all data when time_range="all")
        - Top blueprints data (filtered by time_range, or all data when time_range="all")
        
        Args:
            time_range: Time filter - 'today', '7days', '30days', or 'all' (no time limit)
        
        Returns:
            Dictionary with keys for each facet, containing lists of GroupedCount DTOs.
        """
        now = datetime.now(timezone.utc)
        
        # Calculate cutoff dates using utility function pattern
        today_cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_cutoff = now - timedelta(days=7)
        month_cutoff = now - timedelta(days=30)
        
        # Get time_range cutoff for top users and top blueprints (respects selected time_range)
        # Returns None for "all" (no time limit)
        time_range_cutoff = analytics_utils.get_cutoff_date(time_range)
        
        # Convert to ISO strings
        today_iso = today_cutoff.isoformat().replace('+00:00', 'Z')
        week_iso = week_cutoff.isoformat().replace('+00:00', 'Z')
        month_iso = month_cutoff.isoformat().replace('+00:00', 'Z')
        time_range_iso = time_range_cutoff.isoformat().replace('+00:00', 'Z') if time_range_cutoff else None
        
        # Helper to build pipeline stages with optional time filter
        def build_user_status_stages(time_filter_iso: Optional[str]) -> List[Dict]:
            stages = []
            if time_filter_iso:
                stages.append({"$match": {"run_context.started_at": {"$gte": time_filter_iso}}})
            stages.append({"$group": {
                "_id": {"user_id": "$user_id", "status": "$status"},
                "count": {"$sum": 1}
            }})
            return stages
        
        def build_user_blueprints_stages(time_filter_iso: Optional[str]) -> List[Dict]:
            stages = []
            if time_filter_iso:
                stages.append({"$match": {"run_context.started_at": {"$gte": time_filter_iso}}})
            stages.append({"$group": {
                "_id": {"user_id": "$user_id", "blueprint_id": "$blueprint_id"},
                "count": {"$sum": 1}
            }})
            return stages
        
        def build_blueprint_data_stages(time_filter_iso: Optional[str]) -> List[Dict]:
            stages = []
            if time_filter_iso:
                stages.append({"$match": {"run_context.started_at": {"$gte": time_filter_iso}}})
            stages.append({"$group": {
                "_id": {"blueprint_id": "$blueprint_id", "user_id": "$user_id"},
                "count": {"$sum": 1}
            }})
            return stages
        
        # Build faceted pipeline
        pipeline = [
            {"$facet": {
                # Active Users: User + Status groupings
                "today_status": build_user_status_stages(today_iso),
                "week_status": build_user_status_stages(week_iso),
                "month_status": build_user_status_stages(month_iso),
                # Active Users: User + Blueprint groupings
                "today_blueprints": build_user_blueprints_stages(today_iso),
                "week_blueprints": build_user_blueprints_stages(week_iso),
                "month_blueprints": build_user_blueprints_stages(month_iso),
                # Top Users: User data filtered by selected time_range (None = all data)
                "top_users_status": build_user_status_stages(time_range_iso),
                "top_users_blueprints": build_user_blueprints_stages(time_range_iso),
                # Top Blueprints: Blueprint + User groupings (time_range filtered)
                "top_blueprints_data": build_blueprint_data_stages(time_range_iso)
            }}
        ]
        
        empty_result = {
            "today_status": [], "week_status": [], "month_status": [],
            "today_blueprints": [], "week_blueprints": [], "month_blueprints": [],
            "top_users_status": [], "top_users_blueprints": [],
            "top_blueprints_data": []
        }
        
        try:
            results = list(self._col.aggregate(pipeline))
            if not results:
                return empty_result
            
            facet_result = results[0]
            
            # Transform to GroupedCount DTOs
            def to_grouped_counts(docs: List[Dict]) -> List[GroupedCount]:
                return [
                    GroupedCount(fields=doc["_id"], count=doc["count"])
                    for doc in docs
                ]
            
            return {
                "today_status": to_grouped_counts(facet_result.get("today_status", [])),
                "week_status": to_grouped_counts(facet_result.get("week_status", [])),
                "month_status": to_grouped_counts(facet_result.get("month_status", [])),
                "today_blueprints": to_grouped_counts(facet_result.get("today_blueprints", [])),
                "week_blueprints": to_grouped_counts(facet_result.get("week_blueprints", [])),
                "month_blueprints": to_grouped_counts(facet_result.get("month_blueprints", [])),
                "top_users_status": to_grouped_counts(facet_result.get("top_users_status", [])),
                "top_users_blueprints": to_grouped_counts(facet_result.get("top_users_blueprints", [])),
                "top_blueprints_data": to_grouped_counts(facet_result.get("top_blueprints_data", []))
            }
        except Exception as e:
            logger.warning(f"Failed to get all analytics data: {e}")
            return empty_result
