"""Document conversion adapters."""

from infrastructure.sources.document.adapters.local_docling_adapter import (
    LocalDoclingAdapter,
)
from infrastructure.sources.document.adapters.remote_docling_adapter import (
    RemoteDoclingAdapter,
)

__all__ = [
    "LocalDoclingAdapter",
    "RemoteDoclingAdapter",
]
