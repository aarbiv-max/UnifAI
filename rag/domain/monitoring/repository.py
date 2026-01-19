"""Monitoring repository port (interface)."""
from abc import ABC, abstractmethod
from typing import List, Optional

from domain.monitoring.model import MetricsEntry, ErrorEntry, LogEntry


class MonitoringRepository(ABC):
    """
    Port for monitoring data persistence.
    
    Handles metrics, errors, and logs related to pipeline execution.
    """

    # --- Metrics ---
    @abstractmethod
    def save_metrics(self, entry: MetricsEntry) -> None:
        """
        Persist a metrics snapshot for a pipeline.
        
        Parameters:
            entry (MetricsEntry): Metrics snapshot to persist.
        """
        ...

    @abstractmethod
    def get_metrics(self, pipeline_id: str, limit: int = 100) -> List[MetricsEntry]:
        """
        Retrieve the recent metrics history for a pipeline.
        
        Parameters:
            pipeline_id (str): Identifier of the pipeline to query.
            limit (int): Maximum number of entries to return (default 100).
        
        Returns:
            List[MetricsEntry]: Metrics entries ordered most recent first.
        """
        ...

    # --- Errors ---
    @abstractmethod
    def save_error(self, entry: ErrorEntry) -> None:
        """
        Persist an error entry associated with pipeline execution.
        
        Parameters:
            entry (ErrorEntry): Error entry to save; must include the pipeline identifier and error details.
        """
        ...

    @abstractmethod
    def get_errors(self, pipeline_id: str, limit: int = 100) -> List[ErrorEntry]:
        """
        Retrieve the error history for a specific pipeline.
        
        Parameters:
            pipeline_id (str): Identifier of the pipeline to query.
            limit (int): Maximum number of entries to return. Defaults to 100.
        
        Returns:
            List[ErrorEntry]: Error entries for the pipeline, ordered most recent first.
        """
        ...

    # --- Logs ---
    @abstractmethod
    def save_log(self, entry: LogEntry) -> None:
        """
        Persist a log entry for later retrieval and analysis.
        
        Parameters:
            entry (LogEntry): Log entry data to persist (e.g., timestamp, level, message, source and pipeline association).
        """
        ...

    @abstractmethod
    def get_logs_by_source(self, source_type: str, limit: int = 10) -> List[LogEntry]:
        """
        Get recent log entries filtered by a specific source type.
        
        Parameters:
            source_type (str): The source type to filter logs by.
            limit (int): Maximum number of entries to return.
        
        Returns:
            List[LogEntry]: Log entries matching `source_type`, ordered most recent first.
        """
        ...

    @abstractmethod
    def get_logs_by_pipeline(self, pipeline_id: str, limit: int = 100) -> List[LogEntry]:
        """
        Retrieve recent log entries for a specific pipeline.
        
        Returns:
            List[LogEntry]: Log entries for the given pipeline ordered most recent first, limited to `limit` entries.
        """
        ...
