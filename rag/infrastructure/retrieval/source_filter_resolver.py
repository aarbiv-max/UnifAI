"""Source filter resolver - resolves doc_ids/tags to source_ids for search filtering."""
from typing import List, Optional, Set, Dict, Any

from pymongo.collection import Collection

from shared.logger import logger


class SourceFilterResolver:
    """
    Infrastructure component that resolves filters to source_ids for vector search.
    
    Directly accesses MongoDB - this is a query-only component for search filtering,
    not managing aggregate state. Keeping this separate from the repository keeps
    the repository focused on CRUD operations.
    
    Uses OR logic: returns sources matching doc_ids OR sources matching tags.
    
    Usage:
        resolver = SourceFilterResolver(sources_collection)
        source_ids = resolver.resolve(
            source_type="DOCUMENT",
            doc_ids=["doc_1", "doc_2"],
            tags=["finance"]
        )
        
        # Returns:
        # - None: No filters applied (search all)
        # - Empty set: Filters applied but no matches
        # - Set[str]: Matching source_ids
    """
    
    def __init__(self, sources_collection: Collection):
        """
        Initialize the resolver with a MongoDB collection of source documents.
        
        Parameters:
            sources_collection (Collection): MongoDB collection containing source documents used to resolve source_ids for filtering.
        """
        self._col = sources_collection
    
    def resolve(
        self,
        source_type: str,
        doc_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Set[str]]:
        """
        Resolve filters into matching source IDs using OR logic across doc IDs and tags.
        
        Parameters:
            source_type (str): Source type to constrain the query; normalized to uppercase.
            doc_ids (Optional[List[str]]): If provided, include documents whose `source_id` is in this list.
            tags (Optional[List[str]]): If provided, include documents that have any of these tags.
        
        Returns:
            Optional[Set[str]]: 
                - `None` if neither `doc_ids` nor `tags` are provided (no filters applied).
                - A set of matching `source_id` strings when filters are applied and matches exist.
                - An empty set if filters are applied but no matches are found or an error occurs while querying.
        """
        if not doc_ids and not tags:
            return None
        
        conditions: List[Dict[str, Any]] = []
        if doc_ids:
            conditions.append({"source_id": {"$in": doc_ids}})
        if tags:
            conditions.append({"tags": {"$in": tags}})
        
        query: Dict[str, Any] = {
            "source_type": source_type.upper(),
            "$or": conditions,
        }
        
        try:
            # Only fetch source_id field for efficiency
            docs = self._col.find(query, {"source_id": 1})
            return {d["source_id"] for d in docs if d.get("source_id")}
        except Exception as e:
            logger.error(f"Error resolving source filters: {e}")
            return set()