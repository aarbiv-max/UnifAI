"""Infrastructure adapter for name duplicate checking.

This adapter implements the NameDuplicateCheckerPort using MongoDB storage.
It preserves the exact same logic as the original NameDuplicateChecker
from backend/services/documents/name_duplicate_checker.py.
"""
from typing import Any, Dict, List, Optional, Tuple

from global_utils.utils import secure_filename


class NameDuplicateCheckerAdapter:
    """
    MongoDB-based name duplicate checker implementation.
    
    A document is considered a blocking duplicate if:
    - It has the same normalized filename (using secure_filename)
    - It belongs to the same user (upload_by)
    - Its pipeline status is NOT 'FAILED' (allows retry of failed uploads)
    """

    def __init__(self, storage: Any) -> None:
        """
        Initialize the NameDuplicateCheckerAdapter with a storage backend used for duplicate checks.
        
        Parameters:
            storage (Any): Storage backend used to fetch documents and pipeline status. Expected to optionally implement
                `get_source_by_query(query: dict) -> List[dict]` and `get_pipeline_status(pipeline_id: str) -> Optional[str]`.
        """
        self._storage = storage

    def normalize_filename(self, filename: str) -> str:
        """
        Produce a normalized filename suitable for duplicate name comparisons.
        
        Parameters:
            filename (str): The original filename to normalize.
        
        Returns:
            str: The normalized filename.
        """
        return secure_filename(filename)

    def get_existing_documents_for_user(self, username: str) -> List[Dict[str, Any]]:
        """
        Retrieve document sources uploaded by a specific user.
        
        If the underlying storage does not support `get_source_by_query` or an error occurs while querying,
        an empty list is returned.
        
        Parameters:
            username (str): Username whose documents to retrieve.
        
        Returns:
            List[Dict[str, Any]]: A list of document dictionaries for the user, or an empty list if none are found
            or on error.
        """
        if not hasattr(self._storage, "get_source_by_query"):
            return []
            
        try:
            query = {
                "source_type": "DOCUMENT",
                "upload_by": username
            }
            result = self._storage.get_source_by_query(query)
            return result if isinstance(result, list) else []
        except Exception:
            return []

    def get_pipeline_status(self, pipeline_id: str) -> Optional[str]:
        """
        Retrieve the status of a pipeline given its ID.
        
        Parameters:
            pipeline_id (str): The pipeline identifier to look up.
        
        Returns:
            The pipeline status string if available, otherwise None.
        """
        if not pipeline_id:
            return None
            
        if hasattr(self._storage, "get_pipeline_status"):
            return self._storage.get_pipeline_status(pipeline_id)
        return None

    def find_blocking_duplicate(
        self,
        normalized_name: str,
        existing_docs: List[Dict[str, Any]],
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine whether a normalized filename is blocked by an existing document.
        
        Parameters:
            normalized_name (str): Normalized filename to check.
            existing_docs (List[Dict[str, Any]]): Documents to compare; each may include 'source_name' and an optional 'pipeline_id'.
        
        Returns:
            Tuple[bool, Optional[str]]: `True` and the existing document's pipeline status if a blocking duplicate exists; `False, None` otherwise. Documents with a pipeline status of "FAILED" do not block.
        """
        for doc in existing_docs:
            doc_name = doc.get("source_name", "")
            doc_normalized = self.normalize_filename(doc_name)
            
            if doc_normalized == normalized_name:
                pipeline_id = doc.get("pipeline_id", "")
                status = self.get_pipeline_status(pipeline_id)
                
                # Only block if existing document is NOT failed
                if status != "FAILED":
                    return True, status
                    
        return False, None

    def is_duplicate_name(
        self,
        filename: str,
        username: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check whether a filename would be considered a blocking duplicate for a given user.
        
        Parameters:
            filename (str): The filename to check; it will be normalized before comparison.
            username (str): The username whose existing documents will be checked.
        
        Returns:
            tuple: `True` if a blocking duplicate exists for the user, `False` otherwise; the second element is the matching document's pipeline status or `None`.
        """
        if not filename:
            return False, None
            
        normalized_name = self.normalize_filename(filename)
        existing_docs = self.get_existing_documents_for_user(username)
        return self.find_blocking_duplicate(normalized_name, existing_docs)