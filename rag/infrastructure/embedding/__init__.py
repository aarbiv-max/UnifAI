"""Embedding infrastructure components."""

from infrastructure.embedding.embedding_generator import DefaultEmbeddingGenerator
from infrastructure.embedding.adapters import (
    LocalEmbeddingAdapter,
    RemoteEmbeddingAdapter,
)

__all__ = [
    "DefaultEmbeddingGenerator",
    "LocalEmbeddingAdapter",
    "RemoteEmbeddingAdapter",
]
