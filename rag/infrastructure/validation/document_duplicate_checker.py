"""Infrastructure adapter for document duplicate checking.

This adapter implements the DuplicateCheckerPort using MongoDB storage.
It preserves the exact same logic as the original DocumentDuplicateChecker
from backend/services/documents/duplicate_checker.py.
"""
from typing import Any, Dict, List, Optional

from global_utils.utils import compute_file_md5


# Statuses that should NOT block duplicate uploads (allow retry of failed uploads)
NON_BLOCKING_STATUSES = {"FAILED"}


class DocumentDuplicateCheckerAdapter:
    """
    MongoDB-based duplicate checker implementation.
    
    A document is considered a duplicate if an existing document with the same 
    MD5 hash exists and is NOT in FAILED status. Documents with FAILED status 
    are not considered duplicates, allowing users to retry failed uploads.
    """

    def __init__(self, storage: Any) -> None:
        """
        Initialize the adapter with a storage backend.
        
        Parameters:
            storage (Any): Storage backend used to query sources and pipeline statuses. Expected to implement
                `get_source_by_query(query)` and optionally `get_pipeline_status(pipeline_id)`.
        """
        self._storage = storage

    def find_existing_by_md5(
        self,
        md5: str,
        *,
        source_type: str = "DOCUMENT",
        extra_filters: Optional[Dict[str, Any]] = None,
        only_blocking: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Find existing source documents that share the given MD5 hash.
        
        Searches the storage for documents with type_data.md5 equal to `md5` and `source_type`. If `extra_filters` is provided it is merged into the query. When `only_blocking` is True, returned results are further filtered to exclude sources whose pipeline status is in NON_BLOCKING_STATUSES (e.g., "FAILED"). If the storage lacks the expected query method or an error occurs, an empty list is returned.
        
        Parameters:
            md5 (str): MD5 hash to search for.
            source_type (str): Source type to filter by (default "DOCUMENT").
            extra_filters (Optional[Dict[str, Any]]): Additional query filters to merge into the search.
            only_blocking (bool): If True, return only sources whose pipeline status is not in NON_BLOCKING_STATUSES.
        
        Returns:
            List[Dict[str, Any]]: List of matching source documents (possibly empty).
        """
        if not hasattr(self._storage, "get_source_by_query"):
            return []

        query: Dict[str, Any] = {
            "source_type": source_type,
            "type_data.md5": md5,
        }
        if extra_filters:
            query.update(extra_filters)

        try:
            result = self._storage.get_source_by_query(query)
            sources = result if isinstance(result, list) else []
            
            if not only_blocking or not sources:
                return sources
            
            # Filter to only include sources with blocking status (NOT FAILED)
            blocking_sources = []
            for source in sources:
                pipeline_id = source.get("pipeline_id")
                status = self._storage.get_pipeline_status(pipeline_id) if hasattr(self._storage, "get_pipeline_status") else None
                if status not in NON_BLOCKING_STATUSES:
                    blocking_sources.append(source)
            
            return blocking_sources
        except Exception:
            return []

    def is_duplicate(
        self,
        doc: Dict[str, Any],
        *,
        source_type: str = "DOCUMENT",
        extra_filters: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Determine whether the given document is a duplicate based on its MD5 hash.
        
        If the function can obtain an MD5 from the provided `doc` (from `doc["md5"]`, `doc["type_data.md5"]`, or by computing the MD5 from a filesystem path in `doc["doc_path"]` or `doc["path"]`), it checks for existing sources with the same MD5 and treats an existing source as a duplicate only if its pipeline status is not in NON_BLOCKING_STATUSES (e.g., "FAILED").
        
        Parameters:
            doc (dict): Document metadata or descriptor that may include an MD5 value or a filesystem path to compute one from.
            source_type (str): Source type to query when looking up existing documents.
            extra_filters (dict, optional): Additional query filters to apply when searching for existing documents.
        
        Returns:
            True if a blocking existing document with the same MD5 is found, False otherwise.
        """
        md5_hash: Optional[str] = None
        if isinstance(doc, dict):
            md5_hash = doc.get("md5") or doc.get("type_data.md5")
            if not md5_hash:
                doc_path = doc.get("doc_path") or doc.get("path")
                if isinstance(doc_path, str):
                    try:
                        md5_hash = compute_file_md5(doc_path)
                    except Exception:
                        md5_hash = None

        if not md5_hash:
            return False

        # Consider documents as blocking duplicates unless they're in FAILED status
        existing = self.find_existing_by_md5(
            md5_hash, 
            source_type=source_type, 
            extra_filters=extra_filters,
            only_blocking=True
        )
        return len(existing) > 0