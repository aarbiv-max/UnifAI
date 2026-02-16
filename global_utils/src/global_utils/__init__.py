"""Global utilities package."""

from global_utils.validators import CoercedStr, coerce_to_str
from global_utils.docling import (
    DoclingClient,
    DoclingService,
    DoclingResponse,
    DoclingProcessingError,
)
from global_utils.embedding import (
    EmbeddingClient,
    EmbeddingService,
    EmbeddingResponse,
    EmbeddingProcessingError,
)

__all__ = [
    # Validators
    "CoercedStr",
    "coerce_to_str",
    # Docling
    "DoclingClient",
    "DoclingService",
    "DoclingResponse",
    "DoclingProcessingError",
    # Embedding
    "EmbeddingClient",
    "EmbeddingService",
    "EmbeddingResponse",
    "EmbeddingProcessingError",
]
