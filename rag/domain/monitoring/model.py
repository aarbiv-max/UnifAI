"""Monitoring domain models."""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class MetricsEntry:
    """
    A snapshot of pipeline metrics at a point in time.
    
    Used for tracking time-series metrics during pipeline execution.
    """
    pipeline_id: str
    source_type: str
    metrics: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetricsEntry":
        """
        Create a MetricsEntry from a dictionary, applying defaults for any missing fields.
        
        Parameters:
            data (Dict[str, Any]): Source mapping. Recognized keys:
                - "pipeline_id": pipeline identifier (defaults to "").
                - "source_type": source type string (defaults to "").
                - "metrics": metrics dictionary (defaults to {}).
                - "timestamp": datetime for the entry (defaults to current UTC time).
        
        Returns:
            MetricsEntry: Instance populated from `data` with defaults applied.
        """
        return cls(
            pipeline_id=data.get("pipeline_id", ""),
            source_type=data.get("source_type", ""),
            metrics=data.get("metrics", {}),
            timestamp=data.get("timestamp", datetime.utcnow()),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the dataclass instance into a dictionary suitable for storage.
        
        Returns:
            Dict[str, Any]: Mapping of field names to their values.
        """
        return asdict(self)


@dataclass
class ErrorEntry:
    """
    A record of an error that occurred during pipeline execution.
    """
    pipeline_id: str
    source_type: str
    error_message: str
    error_details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorEntry":
        """
        Create an ErrorEntry instance from a dictionary of fields.
        
        Parameters:
            data (Dict[str, Any]): Dictionary with optional keys:
                - "pipeline_id" (str): pipeline identifier, defaults to empty string.
                - "source_type" (str): origin of the error, defaults to empty string.
                - "error_message" (str): human-readable error message, defaults to empty string.
                - "error_details" (Dict[str, Any]): additional error metadata, defaults to {}.
                - "timestamp" (datetime): occurrence time, defaults to current UTC time.
        
        Returns:
            ErrorEntry: An ErrorEntry populated from the provided dictionary.
        """
        return cls(
            pipeline_id=data.get("pipeline_id", ""),
            source_type=data.get("source_type", ""),
            error_message=data.get("error_message", ""),
            error_details=data.get("error_details", {}),
            timestamp=data.get("timestamp", datetime.utcnow()),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the dataclass instance into a dictionary suitable for storage.
        
        Returns:
            Dict[str, Any]: Mapping of field names to their values.
        """
        return asdict(self)


@dataclass
class LogEntry:
    """
    A parsed log entry from pipeline execution.
    """
    source_type: str
    message: str
    level: str
    module: str
    timestamp: datetime
    pipeline_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogEntry":
        """
        Create a LogEntry from a dictionary of fields.
        
        Parameters:
            data (Dict[str, Any]): Mapping with optional keys:
                - "source_type": source/type of the log (defaults to "").
                - "message": log message text (defaults to "").
                - "level": log severity level (defaults to "").
                - "module": originating module name (defaults to "").
                - "timestamp": datetime for the entry (defaults to current UTC if missing).
                - "pipeline_id": associated pipeline identifier (defaults to None).
        
        Returns:
            LogEntry: An instance populated from the provided mapping with defaults applied for missing keys.
        """
        return cls(
            source_type=data.get("source_type", ""),
            message=data.get("message", ""),
            level=data.get("level", ""),
            module=data.get("module", ""),
            timestamp=data.get("timestamp", datetime.utcnow()),
            pipeline_id=data.get("pipeline_id"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the dataclass instance into a dictionary suitable for storage.
        
        Returns:
            Dict[str, Any]: Mapping of field names to their values.
        """
        return asdict(self)
