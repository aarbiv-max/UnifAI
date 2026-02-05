import pymongo
from pymongo.collection import Collection
from typing import List, Mapping, Any, Dict, Optional
from datetime import datetime, timedelta, timezone
import logging

from session.repository.repository import SessionRepository
from session.workflow_session import WorkflowSession
from core.dto import GroupedCount
from core import time_utils

logger = logging.getLogger(__name__)


class MongoSessionRepository(SessionRepository):
    """
    A “light” MongoDB‐backed SessionRepository.

    Persists only:
      - run_context (so we keep the original run_id & timestamps)
      - blueprint_path (to recreate via factory)
      - metadata (user tags, etc.)
      - graph_state (the key→value bag)

    On load, we simply re-run the factory and then inject the saved state & context.
    """

    def __init__(
            self,
            mongodb_port: str = "27017",
            mongodb_ip: str = "localhost",
            db_name: str = "UnifAI",
            collection_name: str = "workflow_sessions",
    ):
        # connect
        mongo_uri = f"mongodb://{mongodb_ip}:{mongodb_port}/"
        client = pymongo.MongoClient(mongo_uri)
        db = client[db_name]
        self._col: Collection = db[collection_name]
        self._col.create_index(
            [("user_id", pymongo.ASCENDING), ("run_id", pymongo.ASCENDING)],
            unique=True
        )

    def save(self, session: WorkflowSession) -> None:
        ctx = session.run_context

        doc = {
            "user_id": ctx.user_id,
            "run_id": ctx.run_id,
            "run_context": ctx.to_dict(),
            "metadata": session.metadata.to_dict(),
            "blueprint_id": session.blueprint_id,
            "graph_state": session.graph_state.model_dump(mode="json"),
            "status": session.get_status(),
        }

        self._col.replace_one(
            {"user_id": ctx.user_id, "run_id": ctx.run_id},
            doc,
            upsert=True
        )

    def fetch(self, run_id: str) -> Mapping[str, Any]:
        doc = self._col.find_one({"run_id": run_id}, {"_id": 0})
        if not doc:
            raise KeyError(f"No session for {run_id}")
        return doc

    def list_runs(self, user_id: str) -> List[str]:
        cursor = self._col.find({"user_id": user_id}, {"run_id": 1})
        return [d["run_id"] for d in cursor]

    def delete(self, run_id: str) -> bool:
        """Delete a session by run_id. Returns True if deleted, False if not found."""
        result = self._col.delete_one({"run_id": run_id})
        return result.deleted_count > 0

    def count(self, user_id: str, filter: Dict[str, Any]) -> int:
        """Count sessions matching filter criteria for a user."""
        query = {"user_id": user_id, **filter}
        return self._col.count_documents(query)

    def group_count(self, user_id: str, group_by: List[str], filter: Dict[str, Any] = None) -> List[GroupedCount]:
        """
        Group documents by specified fields and return counts.
        Uses MongoDB aggregation for efficient server-side grouping.
        
        Transforms MongoDB's {"_id": {...}, "count": N} format to 
        database-agnostic GroupedCount DTOs.
        """
        match = {"user_id": user_id, **(filter or {})}
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

    # ---------- System-wide methods (for admin analytics) ----------

    def count_system(self, filter: Dict[str, Any] = None) -> int:
        """
        Count all sessions system-wide (no user_id constraint).
        
        Args:
            filter: Optional filter criteria
            
        Returns:
            Total count of sessions matching the criteria
        """
        return self._col.count_documents(filter or {})

    def get_distinct_users(self, filter: Dict[str, Any] = None) -> List[str]:
        """
        Get distinct user IDs from all sessions.
        
        Args:
            filter: Optional filter criteria
            
        Returns:
            List of distinct user IDs
        """
        return self._col.distinct("user_id", filter or {})

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
        match = filter or {}
        group_id = {field: f"${field}" for field in group_by}
        
        pipeline = [
            {"$match": match},
            {"$group": {"_id": group_id, "count": {"$sum": 1}}}
        ]
        
        return [
            GroupedCount(fields=doc["_id"], count=doc["count"])
            for doc in self._col.aggregate(pipeline)
        ]

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
        now = datetime.now(timezone.utc)
        cutoff_date, date_format = time_utils.get_time_range_params(time_range, now)
        cutoff_iso = cutoff_date.isoformat().replace('+00:00', 'Z') if cutoff_date else None
        
        pipeline = time_utils.build_time_series_pipeline(cutoff_iso, date_format, field_path)
        
        try:
            results = list(self._col.aggregate(pipeline))
            return [{"period": doc["_id"], "count": doc["count"]} for doc in results]
        except Exception as e:
            logger.warning(f"Failed to get time series data: {e}")
            return []

    def get_all_stats_faceted(self, time_range: str = "all") -> Dict[str, List[GroupedCount]]:
        """
        Get all stats data using MongoDB $facet aggregation.
        
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
        
        # Calculate cutoff dates
        today_cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_cutoff = now - timedelta(days=7)
        month_cutoff = now - timedelta(days=30)
        
        # Get time_range cutoff for top users and top blueprints (respects selected time_range)
        # Returns None for "all" (no time limit)
        time_range_cutoff = time_utils.get_cutoff_date(time_range)
        
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
            logger.warning(f"Failed to get all stats data: {e}")
            return empty_result