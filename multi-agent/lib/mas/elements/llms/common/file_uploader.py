"""
FileUploader — domain port for uploading files to an external provider.

Adapters implement upload_batch(); the convenience upload() method
has a default implementation that delegates to upload_batch().
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from .file_reference import FileReference


class FileUploader(ABC):
    """Port for uploading files and obtaining FileReference handles."""

    def upload(
        self,
        filename: str,
        content: bytes,
        mime_type: str,
        credentials: Dict[str, Any],
    ) -> FileReference:
        """Upload a single file. Raises RuntimeError on failure."""
        refs, errors = self.upload_batch(
            [(filename, content, mime_type)], credentials,
        )
        if errors:
            raise RuntimeError(errors[0]["error"])
        if not refs:
            raise RuntimeError("Upload returned no results")
        return refs[0]

    @abstractmethod
    def upload_batch(
        self,
        files: List[Tuple[str, bytes, str]],
        credentials: Dict[str, Any],
    ) -> Tuple[List[FileReference], List[Dict[str, str]]]:
        """Upload multiple files in parallel.

        Args:
            files: List of (filename, content_bytes, mime_type) tuples.
            credentials: Provider-specific credentials dict.

        Returns:
            Tuple of (successful_refs, errors).
            Each error dict has keys ``filename`` and ``error``.
        """
        ...
