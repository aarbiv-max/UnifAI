"""
GeminiCredentialResolver — outbound adapter implementing
FileUploadCredentialResolver for Google GenAI.

Receives a callable that extracts the API key from a blueprint,
keeping this adapter free of application-layer imports.
"""
from typing import Any, Callable, Dict

from mas.elements.llms.common.file_upload_credential_resolver import (
    FileUploadCredentialResolver,
)


class GeminiCredentialResolver(FileUploadCredentialResolver):
    """Resolves Google GenAI API keys via an injected callable."""

    def __init__(self, resolve_fn: Callable[[str], Dict[str, Any]]) -> None:
        self._resolve_fn = resolve_fn

    def resolve(self, blueprint_id: str) -> Dict[str, Any]:
        return self._resolve_fn(blueprint_id)
