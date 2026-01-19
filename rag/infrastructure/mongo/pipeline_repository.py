"""MongoDB adapter for PipelineRepository port."""
from datetime import datetime
from typing import Optional, List, Dict, Any

from pymongo.collection import Collection

from domain.pipeline.model import PipelineRecord, PipelineStatus
from domain.pipeline.repository import PipelineRepository
from shared.logger import logger


class MongoPipelineRepository(PipelineRepository):
    """MongoDB implementation of the PipelineRepository port."""

    def __init__(self, collection: Collection):
        """
        Initialize the repository with a MongoDB collection.
        
        Parameters:
            collection (Collection): MongoDB collection used for all persistence operations by this repository.
        """
        self._col = collection

    def find_by_id(self, pipeline_id: str) -> Optional[PipelineRecord]:
        """
        Retrieve a pipeline record by its pipeline_id.
        
        Returns:
            PipelineRecord or None: `PipelineRecord` if found, `None` otherwise.
        """
        doc = self._col.find_one({"pipeline_id": pipeline_id})
        return self._to_model(doc) if doc else None

    def save(self, record: PipelineRecord) -> None:
        """
        Upserts the given pipeline record into the repository.
        
        Performs an update-or-insert using the record's pipeline_id as the selector; when inserting a new document, initializes its created_at from the record.
        
        Parameters:
            record (PipelineRecord): The pipeline record to persist (used as the source of fields and the upsert key).
        """
        doc = self._to_document(record)
        self._col.update_one(
            {"pipeline_id": record.pipeline_id},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": record.created_at}
            },
            upsert=True,
        )

    def update_status(self, pipeline_id: str, status: PipelineStatus) -> bool:
        """
        Update the pipeline's status and set its last_updated timestamp.
        
        If the new status is `PipelineStatus.DONE`, computes the processing time in seconds from the pipeline's `created_at` to now and stores it in `stats.processing_time`. Updates are applied to the document identified by `pipeline_id`.
        
        Returns:
            True if a document was modified, False otherwise.
        """
        now = datetime.utcnow()
        update_fields: Dict[str, Any] = {
            "status": status.value,
            "last_updated": now,
        }

        # Calculate processing time when done
        if status == PipelineStatus.DONE:
            doc = self._col.find_one({"pipeline_id": pipeline_id})
            if doc:
                created_at = doc.get("created_at", now)
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at)
                processing_time = (now - created_at).total_seconds()
                update_fields["stats.processing_time"] = processing_time

        result = self._col.update_one(
            {"pipeline_id": pipeline_id},
            {"$set": update_fields}
        )
        return result.modified_count > 0

    def get_stats_batch(self, pipeline_ids: List[str]) -> Dict[str, PipelineRecord]:
        """
        Batch-fetch pipeline records and return them keyed by pipeline_id.
        
        Returns:
            Dict[str, PipelineRecord]: Mapping from pipeline_id to the corresponding PipelineRecord for each found document.
        """
        if not pipeline_ids:
            return {}

        docs = self._col.find(
            {"pipeline_id": {"$in": pipeline_ids}},
            {"pipeline_id": 1, "status": 1, "stats": 1, "source_type": 1,
             "created_at": 1, "last_updated": 1, "metadata": 1}
        )

        return {doc["pipeline_id"]: self._to_model(doc) for doc in docs}

    def delete(self, pipeline_id: str) -> int:
        """
        Delete pipelines whose pipeline_id starts with the provided identifier.
        
        Parameters:
            pipeline_id (str): Identifier prefix used to match pipelines to delete.
        
        Returns:
            int: Number of documents deleted; returns 0 if an error occurred during deletion.
        """
        try:
            # Support regex for related pipelines (e.g., sub-pipelines)
            result = self._col.delete_many({"pipeline_id": {"$regex": f"^{pipeline_id}"}})
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting pipeline {pipeline_id}: {e}")
            return 0

    def increment_stats(self, pipeline_id: str, stats_updates: Dict[str, Any]) -> bool:
        """
        Atomically increments numeric statistics fields for a pipeline and updates its last_updated timestamp.
        
        Updates the nested `stats` fields specified by `stats_updates` by adding the provided amounts and sets `last_updated` to the current UTC time. If `stats_updates` is empty, no update is performed and the function reports success.
        
        Parameters:
            pipeline_id (str): Identifier of the pipeline to update.
            stats_updates (Dict[str, Any]): Mapping of statistics field names (keys under `stats`) to increment amounts.
        
        Returns:
            `true` if a document was modified by the update, `false` otherwise.
        """
        if not stats_updates:
            return True

        inc_fields = {f"stats.{k}": v for k, v in stats_updates.items()}
        inc_fields["last_updated"] = datetime.utcnow()

        result = self._col.update_one(
            {"pipeline_id": pipeline_id},
            {
                "$inc": {k: v for k, v in inc_fields.items() if k != "last_updated"},
                "$set": {"last_updated": inc_fields["last_updated"]},
            }
        )
        return result.modified_count > 0

    def get_source_stats(self, source_type: str) -> Dict[str, Any]:
        """
        Aggregate pipeline counts and latest update timestamp for the given source type.
        
        Parameters:
            source_type (str): The source type to filter pipelines by.
        
        Returns:
            Dict[str, Any]: A dictionary with the following keys:
                - total_pipelines (int): Total number of pipelines for the source type.
                - active_pipelines (int): Number of pipelines with status equal to `ACTIVE`.
                - completed_pipelines (int): Number of pipelines with status equal to `DONE`.
                - failed_pipelines (int): Number of pipelines with status equal to `FAILED`.
                - pending_pipelines (int): Number of pipelines with status equal to `PENDING`.
                - latest_update (datetime | None): The most recent `last_updated` timestamp for the source type, or `None` if no pipelines exist.
        """
        pipeline = [
            {"$match": {"source_type": source_type}},
            {"$group": {
                "_id": "$source_type",
                "total_pipelines": {"$sum": 1},
                "active_pipelines": {"$sum": {"$cond": [{"$eq": ["$status", PipelineStatus.ACTIVE.value]}, 1, 0]}},
                "completed_pipelines": {"$sum": {"$cond": [{"$eq": ["$status", PipelineStatus.DONE.value]}, 1, 0]}},
                "failed_pipelines": {"$sum": {"$cond": [{"$eq": ["$status", PipelineStatus.FAILED.value]}, 1, 0]}},
                "pending_pipelines": {"$sum": {"$cond": [{"$eq": ["$status", PipelineStatus.PENDING.value]}, 1, 0]}},
                "latest_update": {"$max": "$last_updated"}
            }}
        ]
        
        result = list(self._col.aggregate(pipeline))
        if result:
            stats = result[0]
            stats.pop("_id", None)
            return stats
        
        return {
            "total_pipelines": 0,
            "active_pipelines": 0,
            "completed_pipelines": 0,
            "failed_pipelines": 0,
            "pending_pipelines": 0,
            "latest_update": None
        }

    # --- Mapping methods ---
    def _to_model(self, doc: Dict[str, Any]) -> PipelineRecord:
        """
        Map a MongoDB document to a PipelineRecord domain model.
        
        Parameters:
            doc (Dict[str, Any]): MongoDB document representing a pipeline.
        
        Returns:
            PipelineRecord: Domain model instance constructed from the document.
        """
        return PipelineRecord.from_dict(doc)

    def _to_document(self, record: PipelineRecord) -> Dict[str, Any]:
        """
        Convert a PipelineRecord to a MongoDB-compatible document.
        
        Parameters:
            record (PipelineRecord): Domain pipeline record to convert.
        
        Returns:
            Dict[str, Any]: Document dictionary suitable for Mongo, with the `created_at` field removed.
        """
        doc = record.to_dict()
        doc.pop("created_at", None)  # Handled separately in upsert
        return doc