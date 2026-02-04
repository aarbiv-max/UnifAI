"""Embedding generator port - domain interface for embedding generation."""

import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Iterator


class EmbeddingPort(ABC):
    """
    Abstract interface for embedding generation.
    
    This port defines the contract for generating vector embeddings from text.
    Implementations can be local (SentenceTransformers) or remote (HTTP service).
    """
    
    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Get the dimension of generated embeddings."""
        pass
    
    @abstractmethod
    def encode_texts(self, texts: List[str]) -> List[np.ndarray]:
        """
        Encode multiple texts into embeddings.
        
        Args:
            texts: List of text strings to encode
            
        Returns:
            List of embedding vectors as numpy arrays
        """
        pass
    
    @abstractmethod
    def encode_single(self, text: str) -> np.ndarray:
        """
        Encode a single text into an embedding.
        
        Args:
            text: Text string to encode
            
        Returns:
            Embedding vector as numpy array
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if the embedding generator is available.
        
        Returns:
            True if available, False otherwise
        """
        pass


class EmbeddingGenerator(ABC):
    """
    Application-level embedding generator.
    
    Uses an EmbeddingPort for the actual encoding and adds:
    - Batch processing
    - Chunk handling
    - Error recovery
    """
    
    def __init__(self, port: EmbeddingPort, batch_size: int = 32):
        """
        Initialize the embedding generator.
        
        Args:
            port: EmbeddingPort implementation
            batch_size: Number of items to process in a single batch
        """
        self._port = port
        self.batch_size = batch_size
    
    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension from the port."""
        return self._port.embedding_dim
    
    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for all chunks.
        
        Args:
            chunks: List of chunks with text and metadata
            
        Returns:
            List of chunks with embeddings added
        """
        if not chunks:
            return []
        
        result_chunks = []
        
        for batch in self._batch_generator(chunks):
            texts = [chunk["text"] for chunk in batch]
            
            try:
                embeddings = self._port.encode_texts(texts)
                
                for i, chunk in enumerate(batch):
                    enriched_chunk = chunk.copy()
                    if i < len(embeddings):
                        enriched_chunk["embedding"] = embeddings[i]
                    else:
                        enriched_chunk["embedding"] = np.zeros(self.embedding_dim)
                    result_chunks.append(enriched_chunk)
                    
            except Exception:
                for chunk in batch:
                    enriched_chunk = chunk.copy()
                    enriched_chunk["embedding"] = np.zeros(self.embedding_dim)
                    result_chunks.append(enriched_chunk)
        
        return result_chunks
    
    def generate_query_embedding(self, query: str) -> np.ndarray:
        """
        Generate an embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector for the query
        """
        if not query:
            raise ValueError("Query text is empty")
        return self._port.encode_single(query)
    
    def _batch_generator(self, chunks: List[Dict[str, Any]]) -> Iterator[List[Dict[str, Any]]]:
        """Split chunks into batches."""
        for i in range(0, len(chunks), self.batch_size):
            yield chunks[i:i + self.batch_size]
