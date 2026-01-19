"""Vector repository port (interface)."""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from domain.vector.model import VectorChunk, SearchResult


class VectorRepository(ABC):
    """Port for vector storage operations."""

    def __init__(self, collection_name: str):
        """
        Initialize the repository with the target collection name used for storing vectors.
        
        Parameters:
            collection_name (str): Name of the vector storage collection to use.
        """
        self.collection_name = collection_name
    

    @abstractmethod
    def initialize(self) -> None:
        """
        Prepare the vector storage backend for use.
        
        Ensures the configured collection or index exists and is ready (created/configured) for storing and querying vectors.
        """
        ...

    @abstractmethod
    def store(self, chunks: List[VectorChunk]) -> int:
        """
        Persist a list of vector chunks to the repository.
        
        Parameters:
            chunks (List[VectorChunk]): VectorChunk objects to persist.
        
        Returns:
            int: Number of chunks successfully stored.
        """
        ...

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Find vectors most similar to the provided query embedding.
        
        Args:
            query_embedding (List[float]): Embedding vector used as the search query.
            top_k (int): Maximum number of results to return.
            filters (Optional[Dict[str, Any]]): Optional metadata filters to restrict results (key-value pairs applied to stored vector metadata).
        
        Returns:
            List[SearchResult]: Matching search results ordered by descending similarity score.
        """
        ...

    @abstractmethod
    def count(self, filters: Optional[Dict[str, Any]] = None, exact: bool = False) -> int:
        """
        Count vectors stored in the collection, optionally constrained by filters or using exact counting.
        
        Parameters:
            filters (Optional[Dict[str, Any]]): Filters to constrain which vectors are counted (for example, metadata conditions).
            exact (bool): If True, perform an exact (potentially slower) count; if False, allow an approximate/fast count.
        
        Returns:
            int: The number of vectors matching the provided criteria.
        """
        ...

    @abstractmethod
    def delete(self, ids: Optional[List[str]] = None) -> int:
        """
        Delete vectors identified by the given IDs.
        
        Parameters:
            ids (Optional[List[str]]): Optional list of vector IDs to delete.
        
        Returns:
            int: Number of vectors deleted.
        """
        ...

    @abstractmethod
    def delete_by_filter(self, filters: Dict[str, Any]) -> int:
        """
        Delete vectors that match the provided filters.
        
        Parameters:
            filters (Dict[str, Any]): Criteria used to select vectors for deletion.
        
        Returns:
            int: Number of vectors deleted.
        """
        ... 

    @abstractmethod
    def delete_by_source_id(self, source_id: str) -> int:
        """
        Delete all vectors associated with the given source ID.
        
        Parameters:
            source_id (str): Source identifier whose vectors should be removed.
        
        Returns:
            int: Number of vectors deleted.
        """
        ...