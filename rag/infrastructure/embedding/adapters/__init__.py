"""Embedding adapters."""

from infrastructure.embedding.adapters.local_embedding_adapter import (
    LocalEmbeddingAdapter,
)
from infrastructure.embedding.adapters.remote_embedding_adapter import (
    RemoteEmbeddingAdapter,
)

__all__ = [
    "LocalEmbeddingAdapter",
    "RemoteEmbeddingAdapter",
]
