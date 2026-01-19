"""Pipeline application service - CRUD and business logic."""
from datetime import datetime
from typing import Optional, Dict, Any, Union

from domain.pipeline.model import PipelineRecord, PipelineStatus, PipelineStats
from domain.pipeline.repository import PipelineRepository


class PipelineService:
    """Application service for Pipeline aggregate."""

    def __init__(self, pipeline_repo: PipelineRepository):
        """
        Initialize the service with a PipelineRepository.
        
        Parameters:
            pipeline_repo (PipelineRepository): Repository used for persisting and retrieving pipeline records; stored for use by the service's methods.
        """
        self._repo = pipeline_repo

    # --- CRUD ---
    def get(self, pipeline_id: str) -> Optional[PipelineRecord]:
        """
        Retrieve a pipeline record by its identifier.
        
        Parameters:
            pipeline_id (str): The pipeline's unique identifier.
        
        Returns:
            Optional[PipelineRecord]: The matching PipelineRecord if found, otherwise `None`.
        """
        return self._repo.find_by_id(pipeline_id)

    def delete(self, pipeline_id: str) -> int:
        """
        Delete pipeline record(s) by ID.
        
        Returns:
            int: The number of records deleted.
        """
        return self._repo.delete(pipeline_id)

    # --- Business Methods ---
    def register(self, pipeline_id: str, source_type: str) -> PipelineRecord:
        """
        Ensure a PipelineRecord exists for the given pipeline ID, creating one if absent.
        
        If a record already exists, its last_updated timestamp is refreshed before saving; otherwise a new record is created with status PENDING, current UTC timestamps, and an empty PipelineStats and saved.
        
        Returns:
            PipelineRecord: The existing or newly created pipeline record.
        """
        existing = self._repo.find_by_id(pipeline_id)
        if existing:
            existing.last_updated = datetime.utcnow()
            self._repo.save(existing)
            return existing

        record = PipelineRecord(
            pipeline_id=pipeline_id,
            source_type=source_type,
            status=PipelineStatus.PENDING,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            stats=PipelineStats(),
        )
        self._repo.save(record)
        return record

    def update_status(
        self,
        pipeline_id: str,
        status: Union[PipelineStatus, str],
    ) -> bool:
        """
        Update the status of a pipeline record and persist timestamp and processing time.
        
        Parameters:
            pipeline_id (str): ID of the pipeline to update.
            status (PipelineStatus | str): New status as a PipelineStatus instance or its string representation.
        
        Returns:
            bool: `True` if the record was found and updated, `False` if no record exists for the given ID.
        """
        # Convert string to enum if needed
        if isinstance(status, str):
            status = PipelineStatus(status)

        record = self._repo.find_by_id(pipeline_id)
        if not record:
            return False

        record.status = status
        record.last_updated = datetime.utcnow()

        # Calculate processing time when done
        if status == PipelineStatus.DONE:
            record.stats.processing_time = (
                record.last_updated - record.created_at
            ).total_seconds()

        self._repo.save(record)
        return True

    def increment_stats(self, pipeline_id: str, stats_updates: Dict[str, Any]) -> bool:
        """
        Atomically increment numeric statistics fields for a pipeline.
        
        Parameters:
            pipeline_id (str): Identifier of the pipeline whose stats will be updated.
            stats_updates (Dict[str, Any]): Mapping of statistic field names to increment values,
                e.g. {"documents_retrieved": 5, "chunks_generated": 10}.
        
        Returns:
            `true` if the update succeeded, `false` otherwise.
        """
        return self._repo.increment_stats(pipeline_id, stats_updates)