"""MongoDB adapter for DataSourceRepository port."""
from typing import Optional, List, Dict, Any

from pymongo.collection import Collection

from domain.data_source.model import DataSource
from domain.data_source.repository import DataSourceRepository
from domain.pagination import PaginatedResult
from infrastructure.mongo.pagination_builder import PaginatedQueryBuilder


class MongoDataSourceRepository(DataSourceRepository):
    """MongoDB implementation of the DataSourceRepository port."""

    def __init__(self, collection: Collection):
        """
        Initialize the repository with a MongoDB collection used for DataSource persistence.
        
        Parameters:
            collection (Collection): PyMongo Collection instance representing the data_sources collection used for queries and updates.
        """
        self._col = collection

    def find_by_id(self, source_id: str) -> Optional[DataSource]:
        """
        Retrieve a DataSource by its source_id.
        
        Returns:
            The matching DataSource if found, otherwise None.
        """
        doc = self._col.find_one({"source_id": source_id})
        return self._to_model(doc) if doc else None

    def find_by_pipeline_id(self, pipeline_id: str) -> Optional[DataSource]:
        """
        Finds a DataSource by its pipeline_id.
        
        Parameters:
            pipeline_id (str): Identifier of the pipeline to match.
        
        Returns:
            DataSource | None: The matching DataSource model if found, None otherwise.
        """
        doc = self._col.find_one({"pipeline_id": pipeline_id})
        return self._to_model(doc) if doc else None

    def find_all(self, source_type: Optional[str] = None) -> List[DataSource]:
        """
        Retrieve all data sources, optionally filtered by source type.
        
        Parameters:
            source_type (Optional[str]): If provided, filter results to sources whose type equals this value (case-insensitive).
        
        Returns:
            List[DataSource]: List of DataSource models matching the query.
        """
        query = {"source_type": source_type.upper()} if source_type else {}
        docs = self._col.find(query)
        return [self._to_model(doc) for doc in docs]

    def find_paginated(
        self,
        cursor: Optional[str] = None,
        limit: int = 50,
        source_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResult[Dict[str, Any]]:
        """
        Retrieve sources in a paginated form, optionally filtered by type and searched by name.
        
        Performs a paginated query that searches the `source_name` field, sorts results by `created_at` descending, and filters by `source_type` (converted to uppercase) when provided.
        
        Parameters:
        	cursor (Optional[str]): Opaque pagination cursor to continue from a previous page.
        	limit (int): Maximum number of items to return.
        	source_type (Optional[str]): Source type to filter by; case-insensitive (normalized to uppercase).
        	search (Optional[str]): Search term applied to the `source_name` field.
        
        Returns:
        	PaginatedResult[Dict[str, Any]]: A paginated result containing matching source documents.
        """
        builder = (PaginatedQueryBuilder(self._col)
            .with_search(search, field="source_name")
            .with_sort("created_at", desc=True)
            .paginate(cursor, limit))
        
        if source_type:
            builder.with_filter({"source_type": source_type.upper()})
        
        return builder.documents()

    def get_distinct_values(
        self,
        field: str,
        source_type: Optional[str] = None,
        search: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> PaginatedResult[str]:
        """
        Retrieve paginated distinct values for a specified document field, optionally filtered and searched.
        
        Parameters:
            field (str): The document field to extract distinct values from.
            source_type (Optional[str]): Optional filter for the source type (case-insensitive).
            search (Optional[str]): Optional substring or term to filter values by.
            cursor (Optional[str]): Pagination cursor identifying the page start.
            limit (int): Maximum number of values to return in a page.
        
        Returns:
            PaginatedResult[str]: A paginated result containing distinct string values for the field, sorted in ascending (alphabetical) order.
        """
        builder = (PaginatedQueryBuilder(self._col)
            .with_search(search, field=field)
            .with_sort(field, desc=False)  # Alphabetical ascending
            .paginate(cursor, limit))
        
        if source_type:
            builder.with_filter({"source_type": source_type.upper()})
        
        return builder.distinct(field)

    def save(self, source: DataSource) -> None:
        """
        Insert or update a DataSource identified by its pipeline_id.
        
        Performs an upsert using the source's pipeline_id as the key; when inserting a new document, sets the document's created_at from the provided source.
        
        Parameters:
            source (DataSource): The DataSource domain model to persist.
        """
        doc = self._to_document(source)
        self._col.update_one(
            {"pipeline_id": source.pipeline_id},
            {
                "$set": doc,
                "$setOnInsert": {"created_at": source.created_at}
            },
            upsert=True,
        )

    def delete(self, source_id: str) -> bool:
        """
        Deletes the data source document with the given source_id.
        
        Returns:
            True if a document was deleted, False otherwise.
        """
        result = self._col.delete_one({"source_id": source_id})
        return result.deleted_count > 0

    def get_source_by_query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve documents from the collection that match the given MongoDB query.
        
        Parameters:
            query (Dict[str, Any]): MongoDB filter used to select documents.
        
        Returns:
            List[Dict[str, Any]]: List of matching documents with the `_id` field excluded; returns an empty list if an error occurs while querying.
        """
        try:
            return list(self._col.find(query, {"_id": 0}))
        except Exception:
            return []

    def get_pipeline_status(self, pipeline_id: str) -> Optional[str]:
        """
        Retrieve the status of a pipeline by its pipeline_id.
        
        Returns:
            The pipeline's status as a string, or `None` if `pipeline_id` is falsy, no matching pipeline is found, or an error occurs.
        """
        if not pipeline_id:
            return None
        try:
            # Access sibling collection in same database
            pipeline_col = self._col.database["pipelines"]
            doc = pipeline_col.find_one({"pipeline_id": pipeline_id}, {"status": 1})
            return doc.get("status") if doc else None
        except Exception:
            return None

    # ─── Mapping Methods ──────────────────────────────────────────────────────

    def _to_model(self, doc: Dict[str, Any]) -> DataSource:
        """
        Convert a MongoDB document into a DataSource domain model.
        
        Parameters:
            doc (Dict[str, Any]): MongoDB document representation of a data source.
        
        Returns:
            DataSource: Domain model created from the provided document.
        """
        return DataSource.from_dict(doc)

    def _to_document(self, source: DataSource) -> Dict[str, Any]:
        """
        Convert a DataSource domain model into a MongoDB-compatible document.
        
        Removes the `created_at` field because creation timestamp is handled separately during upsert.
        
        Returns:
            dict: A dictionary representing the MongoDB document for the given DataSource, with `created_at` removed.
        """
        doc = source.to_dict()
        doc.pop("created_at", None)  # Handled separately in upsert
        return doc