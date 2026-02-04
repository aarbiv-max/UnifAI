"""Default EmbeddingGenerator implementation."""

import time
import logging
from typing import Dict, List, Any

from core.vector.domain.embedder import EmbeddingGenerator, EmbeddingPort

logger = logging.getLogger(__name__)


class DefaultEmbeddingGenerator(EmbeddingGenerator):
    """
    Default implementation of EmbeddingGenerator.
    
    Uses an EmbeddingPort for encoding and adds logging with timing.
    """
    
    def __init__(self, port: EmbeddingPort, batch_size: int = 32):
        """Initialize with an embedding port."""
        super().__init__(port, batch_size)
        logger.info(
            f"DefaultEmbeddingGenerator initialized: "
            f"dim={self.embedding_dim}, batch_size={batch_size}"
        )
    
    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate embeddings with logging and timing."""
        if not chunks:
            logger.warning("No chunks provided for embedding generation")
            return []
        
        start_time = time.time()
        logger.info(f"Starting embedding generation for {len(chunks)} chunks")
        
        result = super().generate_embeddings(chunks)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Embedding generation completed in {elapsed_time:.2f} seconds")
        
        return result
