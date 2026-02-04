"""Local Embedding Adapter - uses SentenceTransformers directly."""

import logging
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from core.vector.domain.embedder import EmbeddingPort

logger = logging.getLogger(__name__)


class LocalEmbeddingAdapter(EmbeddingPort):
    """
    Adapter that uses local SentenceTransformers for embedding generation.
    
    This adapter loads a SentenceTransformer model and generates embeddings locally.
    Use when running in environments where the embedding service is not available.
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = None,
    ):
        """
        Initialize with a SentenceTransformer model.
        
        Args:
            model_name: Name of the SentenceTransformer model
            device: Device to run on ("cuda", "cpu", or None for auto)
        """
        logger.info(f"Loading SentenceTransformer model: {model_name}")
        self._model = SentenceTransformer(model_name, device=device)
        self._embedding_dim = self._model.get_sentence_embedding_dimension()
        logger.info(
            f"LocalEmbeddingAdapter initialized: model={model_name}, "
            f"dim={self._embedding_dim}"
        )
    
    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension."""
        return self._embedding_dim
    
    def encode_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Encode texts using local SentenceTransformer model."""
        if not texts:
            return []
        
        embeddings = self._model.encode(texts, show_progress_bar=False)
        
        if isinstance(embeddings, np.ndarray) and embeddings.ndim == 2:
            return [embeddings[i] for i in range(len(embeddings))]
        return list(embeddings)
    
    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text."""
        if not text:
            raise ValueError("Text cannot be empty")
        return self._model.encode(text)
    
    def test_connection(self) -> bool:
        """Local adapter is always available."""
        return True
