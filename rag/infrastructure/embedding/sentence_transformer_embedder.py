"""
Sentence Transformer Embedder

This module provides a unified embedding generator that can work in two modes:
- Local mode: Uses the SentenceTransformers library to generate embeddings locally
- Remote mode: Uses an external embedding service via HTTP

The mode is determined by whether a service_client is injected at construction time.
This decision is made in the bootstrap layer (factory/app_container), not here.
"""

import time
from typing import Dict, List, Any, Optional
from core.vector.domain.embedder import EmbeddingGenerator
from shared.logger import logger
import numpy as np

if TYPE_CHECKING:
    from global_utils.clients import EmbeddingServiceClient


class SentenceTransformerEmbedding(EmbeddingGenerator):
    """
    Unified embedding generator supporting both local and remote modes.
    
    Local mode (service_client=None):
        Uses the SentenceTransformers library to generate embeddings locally.
        Loads the model into memory on initialization.
    
    Remote mode (service_client=EmbeddingServiceClient):
        Uses an external embedding service via HTTP requests.
        No local model is loaded.
    
    The mode is determined by dependency injection - the factory/container
    decides which mode to use based on configuration.
    """

    def __init__(
        self, 
        model_name: str = "all-MiniLM-L6-v2", 
        batch_size: int = 32,
        device: Optional[str] = None,
        service_client: Optional["EmbeddingServiceClient"] = None,
        embedding_dim: int = 384,
    ):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Name of the pre-trained sentence transformer model (for local mode)
            batch_size: Number of chunks to process in a single batch
            device: Device to run the model on (e.g., "cpu", "cuda"). None for auto. (for local mode)
            service_client: Optional EmbeddingServiceClient for remote mode.
                           If provided, uses remote embedding service.
                           If None, loads local SentenceTransformer model.
            embedding_dim: Dimension of embeddings (used for remote mode, local mode auto-detects)
        """
        self._service_client = service_client
        self.model_name = model_name
        self.device = device
        
        if service_client:
            # Remote mode - no local model needed
            self._model = None
            dim = embedding_dim
            logger.info(
                f"SentenceTransformerEmbedding initialized in REMOTE mode, "
                f"dimension: {dim}, batch_size: {batch_size}"
            )
        else:
            # Local mode - load SentenceTransformer model
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformer model: {model_name}")
            self._model = SentenceTransformer(model_name, device=device)
            dim = self._model.get_sentence_embedding_dimension()
            logger.info(
                f"SentenceTransformerEmbedding initialized in LOCAL mode, "
                f"dimension: {dim}, batch_size: {batch_size}"
            )
        
        super().__init__(batch_size, dim)

    @property
    def is_remote(self) -> bool:
        """Check if the embedder is using remote mode."""
        return self._service_client is not None

    def _encode_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Encode a batch of texts into embeddings.
        
        Delegates to either local model or remote service based on mode.
        
        Args:
            texts: List of text strings to encode
            
        Returns:
            List of embedding vectors as numpy arrays
        """
        if self._service_client:
            # Remote mode
            embeddings = self._service_client.generate_embeddings(texts)
            return [np.array(e) for e in embeddings]
        else:
            # Local mode
            embeddings = self._model.encode(texts, show_progress_bar=False)
            # Ensure we return a list of arrays (model.encode returns ndarray)
            if isinstance(embeddings, np.ndarray) and embeddings.ndim == 2:
                return [embeddings[i] for i in range(len(embeddings))]
            return list(embeddings)

    def _encode_single(self, text: str) -> np.ndarray:
        """
        Encode a single text into an embedding.
        
        Args:
            text: Text string to encode
            
        Returns:
            Embedding vector as numpy array
        """
        if self._service_client:
            # Remote mode
            embedding = self._service_client.generate_single_embedding(text)
            return np.array(embedding)
        else:
            # Local mode
            return self._model.encode(text)

    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for all chunks.
        
        Args:
            chunks: List of chunks with text and metadata
            
        Returns:
            List of chunks with embeddings added
        """
        if not chunks:
            logger.warning("No chunks provided for embedding generation")
            return []
        
        start_time = time.time()
        mode_str = "remote service" if self.is_remote else "local model"
        logger.info(f"Starting embedding generation for {len(chunks)} chunks via {mode_str}")
        
        result_chunks = []
        batch_index = 0
        
        for batch in self._batch_generator(chunks):
            batch_index += 1
            logger.debug(f"Processing batch {batch_index} with {len(batch)} chunks")
            
            # Extract text from chunks
            texts = [chunk["text"] for chunk in batch]
            
            try:
                # Generate embeddings for the batch
                embeddings = self._encode_batch(texts)
                
                # Add embeddings to chunks
                for i, chunk in enumerate(batch):
                    enriched_chunk = chunk.copy()
                    if i < len(embeddings):
                        enriched_chunk["embedding"] = embeddings[i]
                    else:
                        logger.warning(f"Missing embedding for chunk {i} in batch {batch_index}")
                        enriched_chunk["embedding"] = np.zeros(self.embedding_dim)
                    result_chunks.append(enriched_chunk)
                    
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {batch_index}: {str(e)}")
                # Fallback: use zero vectors for failed batch
                for chunk in batch:
                    enriched_chunk = chunk.copy()
                    enriched_chunk["embedding"] = np.zeros(self.embedding_dim)
                    result_chunks.append(enriched_chunk)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Embedding generation completed in {elapsed_time:.2f} seconds")
        
        return result_chunks
    
    def generate_query_embedding(self, query: str) -> np.ndarray:
        """
        Generate an embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector for the query
            
        Raises:
            ValueError: If query is empty or embedding generation fails
        """
        if not query:
            raise ValueError("Query text is empty")
        
        try:
            return self._encode_single(query)
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            raise ValueError(f"Failed to generate query embedding: {str(e)}")
