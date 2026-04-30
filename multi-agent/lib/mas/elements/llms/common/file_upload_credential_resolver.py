"""
FileUploadCredentialResolver — domain port for resolving upload credentials.

The resolver inspects a blueprint and returns a credentials dict
consumed by a FileUploader adapter.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class FileUploadCredentialResolver(ABC):
    """Port for resolving file-upload credentials from a blueprint."""

    @abstractmethod
    def resolve(self, blueprint_id: str) -> Dict[str, Any]:
        """Resolve credentials for the given blueprint.

        Returns:
            A dict consumed by FileUploader.upload_batch().

        Raises:
            ValueError: If no compatible LLM config is found.
        """
        ...
