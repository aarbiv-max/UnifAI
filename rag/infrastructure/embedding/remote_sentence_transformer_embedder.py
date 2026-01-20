"""
Remote Sentence Transformer Embedder

This module provides an embedding generator that uses the external embedding service
instead of loading models locally.
"""

import time
from typing import Dict, List, Any, Optional
from domain.vector.embedder import EmbeddingGenerator
from infrastructure.clients.embedding_service_client import EmbeddingServiceClient
from shared.logger import logger
import numpy as np


class RemoteSentenceTransformerEmbedding(EmbeddingGenerator):
    """
    Embedding generator using the external embedding service.
    
    Implements efficient, high-quality embeddings for text chunks
    by making HTTP requests to the embedding service instead of loading
    models locally.
    """

    def __init__(
        self, 
        service_url: Optional[str] = None,
        timeout: Optional[int] = None,
        model_name: Optional[str] = None,
        batch_size: int = 32, 
        embedding_dim: Optional[int] = None
    ):
        """
        Initialize the remote embedding generator.
        
        Args:
            service_url: URL of the embedding service.
            timeout: Request timeout in seconds.
            model_name: Model name to use.
            batch_size: Number of chunks to process in a single batch
            embedding_dim: Dimension of the generated embeddings (model specific, default: 384 for all-MiniLM-L6-v2)
        """
        if service_url is None:
            raise ValueError("service_url is required for RemoteSentenceTransformerEmbedding")
        
        self._service_client = EmbeddingServiceClient(
            base_url=service_url,
            timeout=timeout,
            model_name=model_name
        )
        
        if embedding_dim is None:
            embedding_dim = 384  # Default for all-MiniLM-L6-v2
        
        super().__init__(batch_size, embedding_dim)
        
        logger.info(
            f"RemoteSentenceTransformerEmbedding initialized with dimension: {embedding_dim}, "
            f"batch_size: {batch_size}, service: {service_url}"
        )

    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for all chunks using the embedding service.
        
        Args:
            chunks: List of chunks with text and metadata
            
        Returns:
            List of chunks with embeddings added
        """
        if not chunks:
            logger.warning("No chunks provided for embedding generation")
            return []
        
        start_time = time.time()
        logger.info(f"Starting embedding generation for {len(chunks)} chunks via remote service")
        
        result_chunks = []
        batch_index = 0
        
        for batch in self._batch_generator(chunks):
            batch_index += 1
            logger.debug(f"Processing batch {batch_index} with {len(batch)} chunks")
            
            texts = [chunk["text"] for chunk in batch]
            
            try:
                embeddings = self._service_client.generate_embeddings(texts)
                
                for i, chunk in enumerate(batch):
                    enriched_chunk = chunk.copy()
                    if i < len(embeddings):
                        enriched_chunk["embedding"] = np.array(embeddings[i])
                    else:
                        logger.warning(f"Missing embedding for chunk {i} in batch {batch_index}")
                        enriched_chunk["embedding"] = np.zeros(self.embedding_dim)
                    result_chunks.append(enriched_chunk)
                    
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {batch_index}: {str(e)}")
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
            embedding = self._service_client.generate_single_embedding(query)
            return np.array(embedding)
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            raise ValueError(f"Failed to generate query embedding: {str(e)}")
    
