"""Slack statistics aggregation service."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from application.data_source_service import DataSourceService


# Active statuses that match the UI definition
ACTIVE_STATUSES: Set[str] = {"RUNNING", "PENDING", "QUEUED"}


@dataclass
class SlackStats:
    """Slack statistics for dashboard."""
    id: int
    total_channels: int
    active_channels: int
    total_messages: int
    api_calls_count: int
    last_sync_at: Optional[str]
    total_embeddings: int
    updated_at: str
    
    def to_dict(self) -> dict:
        """
        Produces a dictionary representation of this SlackStats instance using camelCase keys suitable for API responses and frontend consumption.
        
        Returns:
            dict: Mapping containing the keys `id`, `totalChannels`, `activeChannels`, `totalMessages`, `apiCallsCount`, `lastSyncAt`, `totalEmbeddings`, and `updatedAt`.
        """
        return {
            "id": self.id,
            "totalChannels": self.total_channels,
            "activeChannels": self.active_channels,
            "totalMessages": self.total_messages,
            "apiCallsCount": self.api_calls_count,
            "lastSyncAt": self.last_sync_at,
            "totalEmbeddings": self.total_embeddings,
            "updatedAt": self.updated_at,
        }


class SlackStatsService:
    """
    Application service for Slack statistics aggregation.
    
    Query use case that aggregates stats from DataSourceService for Slack sources.
    Provides channel counts, message totals, API call counts, and sync timestamps.
    
    Usage:
        service = SlackStatsService(data_source_service)
        stats = service.get_stats()
        print(f"Active channels: {stats.active_channels}")
    """
    
    def __init__(self, data_source_service: DataSourceService):
        """
        Store the provided DataSourceService instance for use by this service.
        
        Parameters:
            data_source_service (DataSourceService): Service used to list and retrieve Slack source statistics; stored on self._source_service.
        """
        self._source_service = data_source_service
    
    def get_stats(self) -> SlackStats:
        """
        Aggregate statistics for all Slack sources into a SlackStats object.
        
        Retrieves Slack sources with stats, computes totals (channels, active channels, messages, API calls), determines the most recent last_sync_at, and includes total embeddings and the current UTC updated_at timestamp.
        
        Returns:
            SlackStats: Aggregated counts and timestamps. Fields include id, total_channels, active_channels, total_messages, api_calls_count, last_sync_at (or `None`), total_embeddings, and updated_at (ISO 8601 UTC string).
        """
        sources = self._source_service.list_with_stats("SLACK")
        
        counts = self._aggregate_counts(sources)
        last_sync = self._get_last_sync_at(sources)
        
        return SlackStats(
            id=1,
            total_channels=counts["total_channels"],
            active_channels=counts["active_channels"],
            total_messages=counts["total_messages"],
            api_calls_count=counts["api_calls_count"],
            last_sync_at=last_sync,
            total_embeddings=len(sources),
            updated_at=datetime.utcnow().isoformat() + "Z",
        )
    
    def _aggregate_counts(self, sources: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Aggregate channel, message, and API call counts from a list of Slack source records.
        
        Parameters:
            sources (List[Dict[str, Any]]): Source dictionaries returned by the data source service. Each source may include a "status" field and an optional "pipeline_stats" mapping containing "documents_retrieved" and "api_calls" numeric values.
        
        Returns:
            Dict[str, int]: Aggregated counts with keys:
                - "total_channels": total number of sources
                - "active_channels": number of sources whose "status" indicates activity
                - "total_messages": sum of "documents_retrieved" across sources
                - "api_calls_count": sum of "api_calls" across sources
        """
        total_channels = len(sources)
        active_channels = sum(
            1 for s in sources 
            if s.get("status") in ACTIVE_STATUSES
        )
        total_messages = sum(
            s.get("pipeline_stats", {}).get("documents_retrieved", 0) 
            for s in sources if s.get("pipeline_stats")
        )
        api_calls_count = sum(
            s.get("pipeline_stats", {}).get("api_calls", 0) 
            for s in sources if s.get("pipeline_stats")
        )
        
        return {
            "total_channels": total_channels,
            "active_channels": active_channels,
            "total_messages": total_messages,
            "api_calls_count": api_calls_count,
        }
    
    def _get_last_sync_at(self, sources: List[Dict[str, Any]]) -> Optional[str]:
        """
        Return the most recent `last_sync_at` timestamp found in the provided sources.
        
        Parameters:
            sources (List[Dict[str, Any]]): Iterable of source dictionaries; each may include a `last_sync_at` ISO 8601 timestamp string.
        
        Returns:
            Optional[str]: ISO 8601 timestamp string of the most recent `last_sync_at`, or `None` if no timestamps are present.
        """
        timestamps = [
            s.get("last_sync_at") 
            for s in sources 
            if s.get("last_sync_at") is not None
        ]
        return max(timestamps) if timestamps else None
