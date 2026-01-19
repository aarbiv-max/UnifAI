"""DataSource repository port (interface)."""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from domain.data_source.model import DataSource
from domain.pagination import PaginatedResult


class DataSourceRepository(ABC):
    """Port for DataSource persistence - one interface per aggregate."""

    @abstractmethod
    def find_by_id(self, source_id: str) -> Optional[DataSource]:
        """
        Retrieve a data source by its source_id.
        
        Parameters:
            source_id (str): Unique identifier of the data source.
        
        Returns:
            DataSource or None: The matching DataSource if found, otherwise None.
        """
        ...

    @abstractmethod
    def find_by_pipeline_id(self, pipeline_id: str) -> Optional[DataSource]:
        """
        Retrieve the data source associated with the given pipeline ID.
        
        Returns:
            DataSource: The matching data source if found, `None` otherwise.
        """
        ...

    @abstractmethod
    def find_all(self, source_type: Optional[str] = None) -> List[DataSource]:
        """
        Return all data sources, optionally filtered by type.
        
        Parameters:
            source_type (Optional[str]): If provided, only sources whose type equals this value (e.g., "DOCUMENT", "SLACK") are returned.
        
        Returns:
            List[DataSource]: DataSource instances matching the filter.
        """
        ...

    @abstractmethod
    def find_paginated(
        self,
        cursor: Optional[str] = None,
        limit: int = 50,
        source_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResult[Dict[str, Any]]:
        """
        Retrieve a page of data sources with optional type and name-prefix filtering.
        
        Parameters:
            cursor (Optional[str]): Pagination cursor for the current page.
            limit (int): Maximum number of items to return.
            source_type (Optional[str]): Optional filter by source type (e.g., "DOCUMENT", "SLACK").
            search (Optional[str]): Optional case-insensitive prefix filter applied to source names.
        
        Returns:
            PaginatedResult[Dict[str, Any]]: A paginated result containing dictionaries that represent source documents and pagination metadata (e.g., next cursor).
        """
        ...

    @abstractmethod
    def get_distinct_values(
        self,
        field: str,
        source_type: Optional[str] = None,
        search: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> PaginatedResult[str]:
        """
        Retrieve distinct string values for a given field across data sources with optional filtering and pagination.
        
        Parameters:
            field (str): Field path to extract distinct values from (e.g., "tags").
            source_type (Optional[str]): Optional filter by source type (e.g., "DOCUMENT", "SLACK").
            search (Optional[str]): Optional case-insensitive prefix filter for returned values.
            cursor (Optional[str]): Pagination cursor for the current page.
            limit (int): Maximum number of distinct values to return.
        
        Returns:
            PaginatedResult[str]: A paginated result containing distinct string values.
        """
        ...

    @abstractmethod
    def save(self, source: DataSource) -> None:
        """
        Insert or update a DataSource in persistent storage using its pipeline_id.
        
        If a data source with the same pipeline_id already exists, persist changes to that record; otherwise create a new record.
        
        Parameters:
            source (DataSource): The DataSource aggregate to persist (upsert by its pipeline_id).
        """
        ...

    @abstractmethod
    def delete(self, source_id: str) -> bool:
        """
        Delete a data source by its identifier.
        
        Returns:
            true if a source was deleted, false otherwise.
        """
        ...