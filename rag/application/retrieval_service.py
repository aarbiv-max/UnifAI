"""Retrieval application service - vector search orchestration."""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Union

from domain.vector.repository import VectorRepository
from domain.vector.embedder import EmbeddingGenerator
from domain.vector.model import SearchResult
from infrastructure.retrieval.source_filter_resolver import SourceFilterResolver
from shared.logger import logger


@dataclass
class SearchQuery:
    """Value object for search parameters."""
    query_text: str
    source_type: str
    top_k: int = 5
    scope: str = "public"  # "public" or "private"
    user: str = "default"
    doc_ids: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class RetrievalService:
    """
    Application service for vector search/retrieval operations.
    
    Orchestrates:
    - Filter resolution (doc_ids, tags -> source_ids)
    - Query embedding generation
    - Vector search execution
    
    Usage:
        service = retrieval_service("DOCUMENT")  # from app_container
        results = service.search(
            query="How to reset password?",
            limit=5,
            doc_ids=["doc_1"],
        )
    """
    
    def __init__(
        self,
        embedder: EmbeddingGenerator,
        vector_repo: VectorRepository,
        filter_resolver: SourceFilterResolver,
        source_type: str = "DOCUMENT",
    ):
        """
        Initialize the retrieval service with components required for embedding generation, vector search, and source filtering.
        
        Parameters:
            source_type (str): Default source type to use when resolving filters (e.g., "DOCUMENT").
        """
        self._embedder = embedder
        self._vector_repo = vector_repo
        self._filter_resolver = filter_resolver
        self._source_type = source_type
    
    def search(
        self,
        query: str,
        limit: int = 5,
        scope: str = "public",
        user: str = "default",
        doc_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a vector search for the given query and return matching documents, optionally constrained by scope, document IDs, or tags.
        
        If document/tag filters are provided and resolve to no matching source IDs, the function returns an empty list.
        
        Parameters:
            query (str): Text to search.
            limit (int): Maximum number of results to return.
            scope (str): "public" or "private". When "private", results are restricted to those uploaded by `user`.
            user (str): User identifier used to restrict results when scope is "private".
            doc_ids (Optional[List[str]]): Optional list of document IDs to restrict the search to specific source IDs.
            tags (Optional[List[str]]): Optional list of tags to restrict the search to specific source IDs.
        
        Returns:
            List[Dict[str, Any]]: List of result dictionaries ordered by relevance, each containing `id`, `score`, `content`, and `metadata`.
        """
        # 1. Resolve source filters (doc_ids/tags -> source_ids)
        allowed_source_ids = self._filter_resolver.resolve(
            source_type=self._source_type,
            doc_ids=doc_ids,
            tags=tags,
        )
        
        # Early exit if filters applied but no matches
        if allowed_source_ids is not None and not allowed_source_ids:
            logger.info("Filter resolved to empty set - returning no results")
            return []
        
        # 2. Build vector search filters
        filters: Dict[str, Any] = {}
        
        if allowed_source_ids:
            filters["metadata.source_id"] = list(allowed_source_ids)
        
        if scope == "private":
            filters["metadata.upload_by"] = user
        
        # 3. Generate query embedding
        query_embedding = self._embedder.generate_query_embedding(query)
        
        # 4. Execute vector search
        results = self._vector_repo.search(
            query_embedding=query_embedding.tolist(),
            top_k=limit,
            filters=filters if filters else None,
        )
        
        logger.info(f"Search returned {len(results)} results for query: {query[:50]}...")
        
        # Convert SearchResult objects to dicts for API response
        return [
            {
                "id": r.id,
                "score": r.score,
                "content": r.content,
                "metadata": r.metadata,
            }
            for r in results
        ]

    def search_with_query(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """
        Perform a retrieval using the provided SearchQuery and return matching results.
        
        Parameters:
            query (SearchQuery): SearchQuery containing the text and filtering parameters to apply.
        
        Returns:
            List[Dict[str, Any]]: Search result dictionaries ordered by relevance. Each dictionary contains keys `id`, `score`, `content`, and `metadata`.
        """
        return self.search(
            query=query.query_text,
            limit=query.top_k,
            scope=query.scope,
            user=query.user,
            doc_ids=query.doc_ids,
            tags=query.tags,
        )