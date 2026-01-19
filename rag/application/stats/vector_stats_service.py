"""Vector storage statistics service."""
from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional

from domain.vector.repository import VectorRepository


@dataclass
class VectorStats:
    """Vector storage statistics."""
    slack: int
    document: int
    total: int
    
    def to_dict(self) -> dict:
        """
        Convert the stats to a dictionary suitable for API responses.
        
        Returns:
            dict: Mapping with keys "slack", "document", and "total" containing their respective integer counts.
        """
        return {
            "slack": self.slack,
            "document": self.document,
            "total": self.total,
        }


class VectorStatsService:
    """
    Application service for vector storage statistics.
    
    Query use case that aggregates chunk counts from different vector collections.
    Uses an injected repository factory to avoid tight coupling to specific collections.
    
    Usage:
        service = VectorStatsService(vector_repo_factory=vector_repository)
        stats = service.get_chunk_counts()
        print(f"Total chunks: {stats.total}")
    """
    
    def __init__(self, vector_repo_factory: Callable[[str], VectorRepository]):
        """
        Create a VectorStatsService using a repository factory.
        
        Parameters:
            vector_repo_factory (Callable[[str], VectorRepository]): Factory that returns a VectorRepository for a given collection name.
        """
        self._repo_factory = vector_repo_factory
    
    def get_chunk_counts(self) -> VectorStats:
        """
        Get exact chunk counts for the configured source collections.
        
        Returns:
            VectorStats: Counts for `slack` and `document`, and `total` as their sum.
        """
        slack_repo = self._repo_factory("slack_data")
        doc_repo = self._repo_factory("document_data")
        
        slack = slack_repo.count(exact=True)
        document = doc_repo.count(exact=True)
        
        return VectorStats(
            slack=slack,
            document=document,
            total=slack + document,
        )
    
    def get_count_for_collection(self, collection_name: str, exact: bool = True) -> int:
        """
        Retrieve the number of vector chunks stored in the specified collection.
        
        Parameters:
            collection_name (str): Name of the vector collection to query.
            exact (bool): Whether to perform an exact count; if False an estimated count may be returned.
        
        Returns:
            int: Number of chunks in the collection.
        """
        repo = self._repo_factory(collection_name)
        return repo.count(exact=exact)

    def count_by_filter(
        self,
        collection_name: str,
        filters: Dict[str, Any],
        exact: bool = True,
    ) -> int:
        """
        Count vector chunks in a collection that match given metadata filters.
        
        Parameters:
            collection_name (str): Collection identifier (e.g., "slack_data" or "document_data").
            filters (Dict[str, Any]): Mapping of metadata field paths to values to match
                (for example {"metadata.channel_name": "general"} or {"metadata.source_id": "doc_123"}).
            exact (bool): Whether to perform an exact (potentially slower) count.
        
        Returns:
            int: Number of chunks matching the provided filter criteria.
        """
        repo = self._repo_factory(collection_name)
        return repo.count(filters=filters, exact=exact)
