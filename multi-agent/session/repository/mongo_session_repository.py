import pymongo
from pymongo.collection import Collection
from typing import List, Mapping, Any, Dict, Optional
from datetime import datetime, timezone
import logging

from session.repository.repository import SessionRepository
from session.workflow_session import WorkflowSession
from core.dto import GroupedCount, TimeSeriesPoint, SystemAnalyticsData
from global_utils.utils.time_utils import format_utc_iso

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

    # Field path used for time-based filtering in this MongoDB schema
    _TIME_FIELD = "run_context.started_at"

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

    def count_system(self, since: Optional[datetime] = None) -> int:
        """Count all sessions system-wide, optionally filtered by time."""
        time_filter = self._build_time_filter(since)
        return self._col.count_documents(time_filter)

    def get_distinct_users(self, since: Optional[datetime] = None) -> List[str]:
        """Get distinct user IDs, optionally filtered by time."""
        time_filter = self._build_time_filter(since)
        return self._col.distinct("user_id", time_filter)

    def group_count_system(
        self, 
        group_by: List[str],
        since: Optional[datetime] = None
    ) -> List[GroupedCount]:
        """Group all sessions by specified fields and return counts (system-wide)."""
        time_filter = self._build_time_filter(since)
        group_id = {field: f"${field}" for field in group_by}
        
        pipeline = [
            {"$match": time_filter},
            {"$group": {"_id": group_id, "count": {"$sum": 1}}}
        ]
        
        return [
            GroupedCount(fields=doc["_id"], count=doc["count"])
            for doc in self._col.aggregate(pipeline)
        ]

    def get_session_activity_series(
        self, 
        since: Optional[datetime] = None
    ) -> List[TimeSeriesPoint]:
        """
        Get session activity data grouped by appropriate time intervals.
        
        Automatically determines granularity:
        - Less than 1 day -> hourly
        - Up to 30 days -> daily
        - All time -> monthly
        """
        date_format = self._get_granularity_format(since)
        pipeline = self._build_time_series_pipeline(since, date_format)
        
        try:
            results = list(self._col.aggregate(pipeline))
            return [
                TimeSeriesPoint(period=doc["_id"], count=doc["count"])
                for doc in results
            ]
        except Exception as e:
            logger.warning(f"Failed to get session activity series: {e}")
            return []

    def get_system_analytics(
        self, 
        since: Optional[datetime] = None
    ) -> SystemAnalyticsData:
        """
        Get aggregated system analytics using MongoDB $facet for efficiency.
        
        Executes user+status, user+blueprint, and blueprint+user aggregations
        in a single database round-trip.
        """
        cutoff_iso = format_utc_iso(since) if since else None
        
        pipeline = [
            {"$facet": {
                "user_status": self._build_group_stages(
                    {"user_id": "$user_id", "status": "$status"}, cutoff_iso
                ),
                "user_blueprint": self._build_group_stages(
                    {"user_id": "$user_id", "blueprint_id": "$blueprint_id"}, cutoff_iso
                ),
                "blueprint_user": self._build_group_stages(
                    {"blueprint_id": "$blueprint_id", "user_id": "$user_id"}, cutoff_iso
                ),
            }}
        ]
        
        try:
            results = list(self._col.aggregate(pipeline))
            if not results:
                return SystemAnalyticsData()
            
            facet_result = results[0]
            
            return SystemAnalyticsData(
                user_status_counts=self._to_grouped_counts(
                    facet_result.get("user_status", [])
                ),
                user_blueprint_counts=self._to_grouped_counts(
                    facet_result.get("user_blueprint", [])
                ),
                blueprint_user_counts=self._to_grouped_counts(
                    facet_result.get("blueprint_user", [])
                )
            )
        except Exception as e:
            logger.warning(f"Failed to get system analytics data: {e}")
            return SystemAnalyticsData()

    # ---------- Private helpers ----------

    def _build_time_filter(self, since: Optional[datetime]) -> Dict[str, Any]:
        """Build a MongoDB match filter from an optional cutoff datetime."""
        if since is None:
            return {}
        cutoff_iso = format_utc_iso(since)
        return {self._TIME_FIELD: {"$gte": cutoff_iso}}

    def _get_granularity_format(self, since: Optional[datetime]) -> str:
        """Determine date format for time series granularity based on the time range."""
        if since is None:
            return "%Y-%m"  # Monthly for all-time data
        delta = datetime.now(timezone.utc) - since
        if delta.days < 1:
            return "%Y-%m-%d %H:00"  # Hourly for today
        return "%Y-%m-%d"  # Daily for other ranges

    def _build_time_series_pipeline(
        self, 
        since: Optional[datetime],
        date_format: str
    ) -> List[Dict[str, Any]]:
        """Build MongoDB aggregation pipeline for time series data."""
        field_path = self._TIME_FIELD
        
        if since:
            cutoff_iso = format_utc_iso(since)
            match_stage = {"$match": {
                field_path: {"$gte": cutoff_iso, "$exists": True}
            }}
        else:
            match_stage = {"$match": {
                field_path: {"$exists": True}
            }}
        
        return [
            match_stage,
            {"$group": {
                "_id": {
                    "$dateToString": {
                        "format": date_format,
                        "date": {"$dateFromString": {"dateString": f"${field_path}"}}
                    }
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}},
            {"$limit": 1000}
        ]

    def _build_group_stages(
        self,
        group_fields: Dict[str, str],
        time_filter_iso: Optional[str]
    ) -> List[Dict]:
        """Build MongoDB aggregation stages for a group operation with optional time filter."""
        stages = []
        if time_filter_iso:
            stages.append({"$match": {self._TIME_FIELD: {"$gte": time_filter_iso}}})
        stages.append({"$group": {"_id": group_fields, "count": {"$sum": 1}}})
        return stages

    @staticmethod
    def _to_grouped_counts(docs: List[Dict]) -> List[GroupedCount]:
        """Transform raw MongoDB aggregation results to GroupedCount DTOs."""
        return [
            GroupedCount(fields=doc["_id"], count=doc["count"])
            for doc in docs
        ]
