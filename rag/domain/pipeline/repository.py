"""Pipeline repository port (interface)."""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from domain.pipeline.model import PipelineRecord, PipelineStatus


class PipelineRepository(ABC):
    """Port for PipelineRecord persistence."""

    @abstractmethod
    def find_by_id(self, pipeline_id: str) -> Optional[PipelineRecord]:
        """
        Retrieve the pipeline record for the given pipeline ID.
        
        Returns:
            PipelineRecord if found, `None` otherwise.
        """
        ...

    @abstractmethod
    def save(self, record: PipelineRecord) -> None:
        """Insert or update pipeline record (upsert by pipeline_id)."""
        ...

    @abstractmethod
    def update_status(self, pipeline_id: str, status: PipelineStatus) -> bool:
        """
        Update the status of a pipeline record.
        
        Parameters:
            pipeline_id (str): Identifier of the pipeline to update.
            status (PipelineStatus): New status to set on the pipeline.
        
        Returns:
            True if the status was updated, False otherwise.
        """
        ...

    @abstractmethod
    def get_stats_batch(self, pipeline_ids: List[str]) -> Dict[str, PipelineRecord]:
        """
        Retrieve multiple pipeline records by their IDs for enrichment.
        
        Parameters:
            pipeline_ids (List[str]): Sequence of pipeline IDs to fetch.
        
        Returns:
            Dict[str, PipelineRecord]: Mapping from pipeline ID to the corresponding PipelineRecord for any records found.
        """
        ...

    @abstractmethod
    def delete(self, pipeline_id: str) -> int:
        """
        Delete pipeline records by ID.
        
        Parameters:
            pipeline_id (str): Identifier of the pipeline to delete.
        
        Returns:
            int: Number of records deleted.
        """
        ...

    @abstractmethod
    def increment_stats(self, pipeline_id: str, stats_updates: Dict[str, Any]) -> bool:
        """
        Atomically increment numeric statistic fields on the specified pipeline record.
        
        Parameters:
            pipeline_id (str): Identifier of the pipeline to update.
            stats_updates (Dict[str, Any]): Mapping of statistic field names to increment values (e.g., {"documents_retrieved": 5, "chunks_generated": 10}). Values should be numeric and will be applied as atomic increments.
        
        Returns:
            bool: `True` if the statistics were updated, `False` otherwise.
        """
        ...

    @abstractmethod
    def get_source_stats(self, source_type: str) -> Dict[str, Any]:
        """
        Aggregates statistics for pipelines of the given source type.
        
        Parameters:
            source_type (str): Source type key used to filter pipelines (for example, a connector or ingestion type).
        
        Returns:
            Dict[str, Any]: Mapping of aggregated statistic names to their values:
                - total_pipelines: Total count of pipelines for the source.
                - active_pipelines: Count of pipelines currently active.
                - completed_pipelines: Count of pipelines that have completed successfully.
                - failed_pipelines: Count of pipelines that have failed.
                - pending_pipelines: Count of pipelines awaiting processing.
                - latest_update: Timestamp of the most recent update among the matched pipelines.
        """
        ...