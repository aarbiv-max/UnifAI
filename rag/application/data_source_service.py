"""DataSource application service - CRUD and business logic."""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any

from typing import Callable

from domain.data_source.model import DataSource
from domain.data_source.repository import DataSourceRepository
from domain.pagination import PaginatedResult
from domain.pipeline.repository import PipelineRepository
from domain.vector.repository import VectorRepository
from shared.logger import logger


@dataclass
class DeleteResult:
    """Result of a source deletion operation."""
    success: bool
    source_id: str = ""
    source_name: str = ""
    source_deleted: bool = False
    pipelines_deleted: int = 0
    vectors_deleted: int = 0
    message: str = ""


class DataSourceService:
    """Application service for DataSource aggregate - CRUD + business logic."""

    def __init__(
        self,
        source_repo: DataSourceRepository,
        pipeline_repo: PipelineRepository,
        vector_repo_factory: Callable[[str], VectorRepository],
    ):
        """
        Initialize the DataSourceService with repository dependencies and a vector repository factory.
        
        Parameters:
            source_repo (DataSourceRepository): Repository for CRUD operations on DataSource entities.
            pipeline_repo (PipelineRepository): Repository for querying and managing pipeline records and stats.
            vector_repo_factory (Callable[[str], VectorRepository]): Factory that returns a VectorRepository for a given collection/collection name (used to delete or manage embeddings).
        """
        self._source_repo = source_repo
        self._pipeline_repo = pipeline_repo
        self._vector_repo_factory = vector_repo_factory

    # --- CRUD ---
    def get_by_id(self, source_id: str) -> Optional[DataSource]:
        """
        Retrieve a DataSource by its identifier.
        
        Returns:
            The DataSource if found, otherwise None.
        """
        return self._source_repo.find_by_id(source_id)

    def get_by_pipeline_id(self, pipeline_id: str) -> Optional[DataSource]:
        """
        Retrieve the DataSource associated with the given pipeline ID.
        
        @returns `DataSource` if a matching source exists, `None` otherwise.
        """
        return self._source_repo.find_by_pipeline_id(pipeline_id)

    def list_sources(self, source_type: Optional[str] = None) -> List[DataSource]:
        """
        Return a list of data sources, optionally filtered by source type.
        
        Parameters:
            source_type (Optional[str]): If provided, only sources with this type are returned.
        
        Returns:
            List[DataSource]: Matching data source domain objects.
        """
        return self._source_repo.find_all(source_type)

    def list_paginated(
        self,
        cursor: Optional[str] = None,
        limit: int = 50,
        source_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResult[Dict[str, Any]]:
        """
        Return a paginated list of data sources optionally filtered by type or search.
        
        Parameters:
            cursor (Optional[str]): Cursor for the page to fetch; use None to start from the first page.
            limit (int): Maximum number of items to return in the page.
            source_type (Optional[str]): Optional source type to filter results (e.g., "DOCUMENT").
            search (Optional[str]): Optional case-insensitive prefix filter applied to source names.
        
        Returns:
            PaginatedResult[Dict[str, Any]]: A paginated result containing source dictionaries and pagination metadata (next_cursor, has_more, total).
        """
        return self._source_repo.find_paginated(cursor, limit, source_type, search)

    def save(self, source: DataSource) -> None:
        """
        Persist a DataSource object to the underlying repository (insert or update).
        
        Parameters:
            source (DataSource): The DataSource instance to persist.
        """
        self._source_repo.save(source)

    def delete(self, source_id: str) -> DeleteResult:
        """
        Delete a data source and its associated pipeline records and vector embeddings.
        
        Performs ordered cleanup and reports outcomes: vector embeddings are removed first (operation is critical and aborts the overall delete on failure), then pipeline and source records are removed; if the source does not exist a failure result is returned.
        
        Parameters:
            source_id (str): Identifier of the source to delete.
        
        Returns:
            DeleteResult: Details of the deletion outcome. Contains `success`, `source_id`, `source_name`, `source_deleted` (whether the source document was removed), `pipelines_deleted` (number of pipeline records removed), `vectors_deleted` (number of vector embeddings removed), and an explanatory `message` when the operation failed or partially failed.
        """
        source = self._source_repo.find_by_id(source_id)
        if not source:
            return DeleteResult(
                success=False,
                message=f"Source {source_id} not found",
            )

        source_name = source.source_name
        # Get the correct vector repository based on source type
        collection_name = f"{source.source_type.lower()}_data"
        vector_repo = self._vector_repo_factory(collection_name)
        
        try:
            vectors_deleted = vector_repo.delete_by_source_id(source_id)
        except Exception as e:
            return DeleteResult(
                success=False,
                source_id=source_id,
                source_name=source_name,
                message=f"Vector storage deletion failed: {e}",
            )
        try:
            pipelines_deleted = self._pipeline_repo.delete(source.pipeline_id)
            source_deleted = self._source_repo.delete(source_id)
        except Exception as e:
            return DeleteResult(
                success=False,
                source_id=source_id,
                source_name=source_name,
                source_deleted=False,
                pipelines_deleted=0,
                vectors_deleted=vectors_deleted,
                message=f"Partial deletion - MongoDB deletion failed: {e}",
            )
        return DeleteResult(
            success=True,
            source_id=source_id,
            source_name=source_name,
            source_deleted=source_deleted,
            pipelines_deleted=pipelines_deleted,
            vectors_deleted=vectors_deleted,
        )

    def update(self, source_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update attributes of an existing DataSource and persist the change.
        
        Parameters:
            source_id (str): Identifier of the source to update.
            updates (Dict[str, Any]): Mapping of DataSource attribute names to new values; only attributes that exist on the DataSource are applied.
        
        Returns:
            bool: `True` if the source was found and updated, `False` otherwise.
        """
        source = self._source_repo.find_by_id(source_id)
        if not source:
            return False
        # Apply updates to domain model
        for key, value in updates.items():
            if hasattr(source, key):
                setattr(source, key, value)
        self._source_repo.save(source)
        return True

    # ══════════════════════════════════════════════════════════════════════════
    # Private Helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _enrich_with_pipeline_stats(self, sources: List[DataSource]) -> List[Dict[str, Any]]:
        """
        Enriches a list of DataSource objects with pipeline status and aggregated pipeline statistics.
        
        Parameters:
            sources (List[DataSource]): DataSource domain models to enrich.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries for each source containing the source fields plus:
                - `status`: the pipeline status string if available, otherwise `None`.
                - `pipeline_stats`: a dict with a `status` key and the pipeline `stats` content when available, otherwise `None`.
        """
        if not sources:
            return []
        
        # Batch fetch stats for all sources in one query
        pipeline_ids = [s.pipeline_id for s in sources if s.pipeline_id]
        stats = self._pipeline_repo.get_stats_batch(pipeline_ids) if pipeline_ids else {}

        result = []
        for source in sources:
            data = asdict(source)
            if source.pipeline_id and source.pipeline_id in stats:
                record = stats[source.pipeline_id]
                data["status"] = record.status.value
                data["pipeline_stats"] = {
                    "status": record.status.value,
                    **asdict(record.stats),
                }
            else:
                data["status"] = None
                data["pipeline_stats"] = None
            result.append(data)
        
        return result

    # ══════════════════════════════════════════════════════════════════════════
    # Business Methods
    # ══════════════════════════════════════════════════════════════════════════

    def upsert_after_pipeline(
        self,
        source_id: str,
        source_name: str,
        source_type: str,
        pipeline_id: str,
        summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create or update a DataSource record after a pipeline run.
        
        If a source with the given pipeline_id exists, update its last_sync_at and merge the optional summary into its type_data; otherwise create a new DataSource populated with the provided identifiers and summary as type_data.
        
        Parameters:
            source_id (str): Unique identifier for the source to create (used when inserting).
            source_name (str): Human-readable name for the source (used when inserting).
            source_type (str): Source category (e.g., "SLACK", "DOCUMENT").
            pipeline_id (str): Associated pipeline identifier used to find or link the source.
            summary (Optional[Dict[str, Any]]): Optional metadata to merge into the source's type_data (e.g., stats or error info).
        """
        existing = self._source_repo.find_by_pipeline_id(pipeline_id)
        now = datetime.utcnow()

        if existing:
            # Update existing source
            existing.last_sync_at = now
            if summary:
                existing.type_data = {**existing.type_data, **summary}
            self._source_repo.save(existing)
        else:
            # Create new source
            source = DataSource(
                source_id=source_id,
                source_name=source_name,
                source_type=source_type,
                pipeline_id=pipeline_id,
                upload_by="",  # Could be passed as param if needed
                created_at=now,
                last_sync_at=now,
                type_data=summary or {},
            )
            self._source_repo.save(source)

    def list_with_stats(self, source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Return sources (optionally filtered by type) enriched with pipeline status and pipeline statistics, sorted by `created_at` descending.
        
        Parameters:
            source_type (Optional[str]): If provided, only include sources of this type.
        
        Returns:
            List[Dict[str, Any]]: A list of source dictionaries augmented with `status` and `pipeline_stats` when available, sorted by `created_at` in descending order.
        """
        sources = self._source_repo.find_all(source_type)
        result = self._enrich_with_pipeline_stats(sources)
        return sorted(result, key=lambda x: x.get("created_at") or 0, reverse=True)

    def get_with_stats(self, source_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a data source by ID and attach pipeline status and pipeline statistics.
        
        Parameters:
            source_id (str): ID of the data source to fetch.
        
        Returns:
            dict: Source data augmented with `status` and `pipeline_stats`, or `None` if the source was not found.
        """
        source = self._source_repo.find_by_id(source_id)
        if not source:
            return None
        
        enriched = self._enrich_with_pipeline_stats([source])
        return enriched[0]

    # ══════════════════════════════════════════════════════════════════════════
    # Paginated Query Methods (for dropdowns/selectors)
    # ══════════════════════════════════════════════════════════════════════════

    def list_available_docs(
        self,
        cursor: Optional[str] = None,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> PaginatedResult[Dict[str, Any]]:
        """
        Return a paginated list of document sources with status "DONE", normalized for UI dropdowns.
        
        Parameters:
            cursor (Optional[str]): Pagination cursor to continue from a previous page.
            limit (int): Maximum number of source records to fetch.
            search (Optional[str]): Optional name prefix filter to apply when fetching sources.
        
        Returns:
            PaginatedResult[Dict[str, Any]]: Paginated result whose `data` is a list of objects with keys `id`, `name`, and `upload_by`. `next_cursor` and `has_more` reflect the upstream pagination, and `total` is the count of items after filtering to DONE status.
        """
        # Get paginated sources
        result = self._source_repo.find_paginated(
            cursor=cursor,
            limit=limit,
            source_type="DOCUMENT",
            search=search,
        )
        
        # Convert to domain models for enrichment
        sources = [DataSource.from_dict(d) for d in result.data]
        enriched = self._enrich_with_pipeline_stats(sources)
        
        # Filter to DONE only and normalize
        done_docs = [
            {"id": s["source_id"], "name": s["source_name"], "upload_by": s["upload_by"]}
            for s in enriched
            if s.get("status") == "DONE"
        ]
        
        return PaginatedResult(
            data=done_docs,
            next_cursor=result.next_cursor,
            has_more=result.has_more,
            total=len(done_docs),  # Approximate due to post-filtering
        )

    def get_available_tags(
        self,
        cursor: Optional[str] = None,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> PaginatedResult[Dict[str, str]]:
        """
        Return distinct tags collected only from sources whose pipeline status is "DONE", formatted for UI dropdowns.
        
        Parameters:
            cursor (Optional[str]): Pagination cursor interpreted as an integer offset (defaults to 0).
            limit (int): Maximum number of tags to return.
            search (Optional[str]): Case-insensitive prefix filter applied to tags.
        
        Returns:
            PaginatedResult[Dict[str, str]]: Paginated result where data is a list of tag objects with keys `label` and `value`.
        """
        # Get all DONE sources
        all_sources = self._source_repo.find_all(source_type="DOCUMENT")
        enriched = self._enrich_with_pipeline_stats(all_sources)
        done_sources = [s for s in enriched if s.get("status") == "DONE"]
        
        # Extract unique tags from DONE sources
        all_tags = set()
        for s in done_sources:
            all_tags.update(s.get("tags", []))
        
        # Apply search filter (case-insensitive prefix match)
        if search:
            search_lower = search.lower()
            all_tags = {t for t in all_tags if t.lower().startswith(search_lower)}
        
        # Sort alphabetically and paginate
        sorted_tags = sorted(all_tags)
        skip = int(cursor) if cursor and cursor.isdigit() else 0
        page = sorted_tags[skip:skip + limit]
        
        next_cursor = str(skip + len(page)) if skip + len(page) < len(sorted_tags) else None
        
        return PaginatedResult(
            data=[{"label": t, "value": t} for t in page],
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
            total=len(sorted_tags),
        )

    def get_distinct_tags(
        self,
        cursor: Optional[str] = None,
        limit: int = 50,
        search: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> PaginatedResult[Dict[str, str]]:
        """
        Return paginated distinct tag options formatted for dropdowns.
        
        Parameters:
            cursor (Optional[str]): Cursor for pagination; use None to start from the beginning.
            limit (int): Maximum number of tags to return.
            search (Optional[str]): Case-insensitive prefix filter applied to tag values.
            source_type (Optional[str]): If provided, restrict tags to the given source type.
        
        Returns:
            PaginatedResult[Dict[str, str]]: Paginated tag objects with keys `label` and `value`.
        """
        result = self._source_repo.get_distinct_values(
            field="tags",
            source_type=source_type,
            search=search,
            cursor=cursor,
            limit=limit,
        )
        
        # Transform to label/value format for dropdowns
        return result.map(lambda tag: {"label": tag, "value": tag})
