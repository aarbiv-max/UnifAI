"""MongoDB adapter for MonitoringRepository port."""
from datetime import datetime
from typing import List, Dict, Any

from pymongo.database import Database

from domain.monitoring.model import MetricsEntry, ErrorEntry, LogEntry
from domain.monitoring.repository import MonitoringRepository


class MongoMonitoringRepository(MonitoringRepository):
    """
    MongoDB implementation of the MonitoringRepository port.
    
    Manages three collections: metrics, errors, logs.
    """

    def __init__(self, database: Database):
        """
        Initialize the repository with MongoDB collections and create indexes used for queries.
        
        Parameters:
            database (Database): MongoDB database instance providing `metrics`, `errors`, and `logs` collections; indexes for `pipeline_id`, `(source_type, timestamp)`, and `pipeline_id` on logs are created for query performance.
        """
        self._db = database
        self._metrics = database.metrics
        self._errors = database.errors
        self._logs = database.logs
        
        # Ensure indexes for performance
        self._metrics.create_index("pipeline_id")
        self._errors.create_index("pipeline_id")
        self._logs.create_index([("source_type", 1), ("timestamp", -1)])
        self._logs.create_index("pipeline_id")

    # --- Metrics ---
    def save_metrics(self, entry: MetricsEntry) -> None:
        """
        Persist a metrics snapshot to the metrics collection.
        
        Parameters:
            entry (MetricsEntry): Metrics snapshot to store; a "timestamp" field with the current time will be added before insertion.
        """
        doc = entry.to_dict()
        doc["timestamp"] = datetime.now()
        self._metrics.insert_one(doc)

    def get_metrics(self, pipeline_id: str, limit: int = 100) -> List[MetricsEntry]:
        """
        Retrieve the most recent metrics for a pipeline.
        
        Parameters:
            pipeline_id (str): Identifier of the pipeline whose metrics are requested.
            limit (int): Maximum number of metric entries to return.
        
        Returns:
            List[MetricsEntry]: Metrics entries sorted by timestamp descending, up to `limit` items.
        """
        docs = self._metrics.find(
            {"pipeline_id": pipeline_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        
        return [MetricsEntry.from_dict(doc) for doc in docs]

    # --- Errors ---
    def save_error(self, entry: ErrorEntry) -> None:
        """
        Persist an error entry to the repository.
        
        Adds a UTC timestamp to the provided ErrorEntry and inserts the resulting document into the errors collection.
        
        Parameters:
            entry (ErrorEntry): The error entry to persist.
        """
        doc = entry.to_dict()
        doc["timestamp"] = datetime.utcnow()
        self._errors.insert_one(doc)

    def get_errors(self, pipeline_id: str, limit: int = 100) -> List[ErrorEntry]:
        """
        Retrieve recent error entries for the specified pipeline.
        
        Parameters:
            pipeline_id (str): Identifier of the pipeline whose error history to retrieve.
            limit (int): Maximum number of error entries to return.
        
        Returns:
            List[ErrorEntry]: Error entries ordered by descending timestamp, limited to `limit`.
        """
        docs = self._errors.find(
            {"pipeline_id": pipeline_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        
        return [ErrorEntry.from_dict(doc) for doc in docs]

    # --- Logs ---
    def save_log(self, entry: LogEntry) -> None:
        """
        Persist a log entry to the repository's logs collection.
        
        Parameters:
            entry (LogEntry): The log entry to store.
        """
        doc = entry.to_dict()
        self._logs.insert_one(doc)

    def get_logs_by_source(self, source_type: str, limit: int = 10) -> List[LogEntry]:
        """
        Retrieve recent log entries for the given source type.
        
        Parameters:
            source_type (str): The source type to filter logs (e.g., component or service name).
            limit (int): Maximum number of log entries to return. Defaults to 10.
        
        Returns:
            List[LogEntry]: LogEntry objects ordered from newest to oldest by timestamp.
        """
        docs = self._logs.find(
            {"source_type": source_type},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        
        return [LogEntry.from_dict(doc) for doc in docs]

    def get_logs_by_pipeline(self, pipeline_id: str, limit: int = 100) -> List[LogEntry]:
        """
        Retrieve log entries for a specific pipeline ordered by newest first.
        
        Parameters:
            pipeline_id (str): Identifier of the pipeline whose logs to retrieve.
            limit (int): Maximum number of log entries to return.
        
        Returns:
            List[LogEntry]: Log entries for the given pipeline ordered by timestamp descending, up to `limit`.
        """
        docs = self._logs.find(
            {"pipeline_id": pipeline_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit)
        
        return [LogEntry.from_dict(doc) for doc in docs]
