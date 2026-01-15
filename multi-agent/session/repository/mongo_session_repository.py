import pymongo
from pymongo.collection import Collection
from typing import List, Mapping, Any, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from session.repository.repository import SessionRepository
from session.workflow_session import WorkflowSession
from core.dto import GroupedCount
from statistics import analytics_utils


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

        # Indexes for system-wide queries to reduce MongoDB load
        self._col.create_index([("run_context.started_at", pymongo.ASCENDING)])
        self._col.create_index([("status", pymongo.ASCENDING)])
        self._col.create_index([("blueprint_id", pymongo.ASCENDING)])
        self._col.create_index([
            ("user_id", pymongo.ASCENDING),
            ("run_context.started_at", pymongo.ASCENDING)
        ])

        # Cache for earliest run date to avoid expensive queries
        self._earliest_run_date_cache: Optional[datetime] = None
        self._earliest_run_date_cache_time: Optional[datetime] = None

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

    def _apply_time_range_filter(self, filter_dict: Dict[str, Any], time_range: Optional[str]) -> Dict[str, Any]:
        """
        Apply time range filtering to a filter dictionary.
        
        Args:
            filter_dict: Base filter dictionary
            time_range: Optional time filter - "today", "7days", "30days", or "all"
            
        Returns:
            Filter dictionary with time range applied if specified
        """
        return analytics_utils.apply_time_range_filter(filter_dict, time_range)

    def group_count_system_wide(self, group_by: List[str], filter: Dict[str, Any] = None, time_range: Optional[str] = None) -> List[GroupedCount]:
        """
        Group documents by specified fields across all users (system-wide).
        Supports time-based filtering via time_range parameter.
        
        Args:
            group_by: List of field names to group by (e.g., ["blueprint_id", "status"])
            filter: Optional additional filter criteria
            time_range: Optional time filter - "today", "7days", "30days", or "all"
            
        Returns:
            List of GroupedCount DTOs with grouped field values and count.
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

    def count_system_wide(self, filter: Dict[str, Any] = None, time_range: Optional[str] = None) -> int:
        """
        Count sessions across all users (system-wide).
        Supports time-based filtering via time_range parameter.
        
        Args:
            filter: Optional additional filter criteria
            time_range: Optional time filter - "today", "7days", "30days", or "all"
            
        Returns:
            Total count of sessions matching the criteria
        """
        query = self._apply_time_range_filter(filter, time_range)
        return self._col.count_documents(query)

    def get_distinct_users(self, filter: Dict[str, Any] = None, time_range: Optional[str] = None) -> List[str]:
        """
        Get distinct user IDs across all sessions (system-wide).
        Supports time-based filtering via time_range parameter.
        
        Args:
            filter: Optional additional filter criteria
            time_range: Optional time filter - "today", "7days", "30days", or "all"
            
        Returns:
            List of distinct user IDs
        """
        match = self._apply_time_range_filter(filter, time_range)
        return self._col.distinct("user_id", match)

    def get_time_series_activity(self, time_range: str = "all") -> List[Dict[str, Any]]:
        """
        Get time series activity data grouped by appropriate time intervals.
        Optimized to use indexes and limit result size.
        
        Args:
            time_range: 'today', '7days', '30days', or 'all'
        
        Returns:
            List of dicts with 'period' (time label) and 'count' (workflow executions)
        """
        earliest_date_getter = lambda now: self._get_earliest_run_date(now)
        return analytics_utils.get_time_series_activity(
            self._col, 
            time_range, 
            earliest_date_getter
        )

    def _get_cutoff_date(self, time_range: str) -> datetime:
        """Get cutoff date based on time_range string."""
        return analytics_utils.get_cutoff_date(time_range)

    def _get_earliest_run_date(self, now: datetime) -> datetime:
        """
        Get the earliest run date from the collection, or default to 365 days ago.
        Uses caching to avoid expensive queries on every call.
        """
        # Cache for 1 hour to reduce MongoDB load
        if (self._earliest_run_date_cache is not None
            and self._earliest_run_date_cache_time is not None
            and (now - self._earliest_run_date_cache_time).total_seconds() < 3600):
            return self._earliest_run_date_cache
        
        # Use aggregation with limit=1 for better performance than find_one with sort
        # This leverages the index on run_context.started_at
        pipeline = [
            {"$match": {"run_context.started_at": {"$exists": True, "$ne": None}}},
            {"$sort": {"run_context.started_at": 1}},
            {"$limit": 1},
            {"$project": {"run_context.started_at": 1}}
        ]
        
        try:
            result = list(self._col.aggregate(pipeline))
            if result:
                earliest_time = result[0].get("run_context", {}).get("started_at")
                if earliest_time:
                    try:
                        if isinstance(earliest_time, str):
                            cutoff_date = datetime.fromisoformat(earliest_time.replace('Z', '+00:00'))
                            if cutoff_date.tzinfo is None:
                                cutoff_date = cutoff_date.replace(tzinfo=timezone.utc)
                        else:
                            cutoff_date = datetime.fromtimestamp(earliest_time, tz=timezone.utc)
                        
                        # Cache the result
                        self._earliest_run_date_cache = cutoff_date
                        self._earliest_run_date_cache_time = now
                        return cutoff_date
                    except (ValueError, TypeError):
                        pass
        except Exception:
            # If query fails, fall through to default
            pass
        
        # Default fallback - limit to 365 days to prevent scanning entire collection
        default_date = now - timedelta(days=365)
        self._earliest_run_date_cache = default_date
        self._earliest_run_date_cache_time = now
        return default_date

    def _get_time_range_params(self, time_range: str, now: datetime) -> Tuple[datetime, str]:
        """
        Get cutoff date and date format based on time_range.
        For 'all', limits to max 365 days to prevent excessive MongoDB load.
        """
        earliest_date = self._get_earliest_run_date(now) if time_range == "all" else None
        return analytics_utils.get_time_range_params(time_range, now, earliest_date)
    
    def get_database(self):
        """
        Get MongoDB database instance for advanced operations.
        This is used by statistics service for cache initialization.
        
        Returns:
            Database: MongoDB database instance
        """
        return self._col.database