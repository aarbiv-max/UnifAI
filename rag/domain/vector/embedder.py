import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Iterator

class EmbeddingGenerator(ABC):
    """
    Abstract base class for embedding generation.
    
    This class defines the common interface and shared functionality
    for creating vector embeddings from text chunks.
    """
    
    def __init__(self, batch_size: int = 32, embedding_dim: Optional[int] = None):
        """
        Create an EmbeddingGenerator configured with a batch size and optional embedding dimensionality.
        
        Parameters:
            batch_size (int): Number of chunks to process per batch when generating embeddings.
            embedding_dim (Optional[int]): Expected dimensionality of produced embeddings, if known.
        """
        self.batch_size = batch_size
        self.embedding_dim = embedding_dim
        
    @abstractmethod
    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for each text chunk and attach the resulting embedding to its dictionary.
        
        Parameters:
            chunks (List[Dict[str, Any]]): A list of chunk dictionaries representing text segments and optional metadata. Each chunk will be augmented in-place (or via a returned copy) with an `embedding` entry containing the generated vector.
        
        Returns:
            List[Dict[str, Any]]: The input list of chunk dictionaries with `embedding` entries added to each chunk.
        """
        pass
    
    @abstractmethod
    def generate_query_embedding(self, query: str) -> np.ndarray:
        """
        Create a vector representation (embedding) for the provided search query.
        
        Parameters:
            query (str): Text of the search query to be embedded.
        
        Returns:
            np.ndarray: Numeric embedding vector representing the query.
        """
        pass
    
    def _batch_generator(self, chunks: List[Dict[str, Any]]) -> Iterator[List[Dict[str, Any]]]:
        """
        Yield successive fixed-size batches from a list of chunk dictionaries.
        
        Each yielded value is a list of original chunk dicts in their original order; the final batch may contain fewer than `batch_size` items.
        
        Parameters:
            chunks (List[Dict[str, Any]]): Sequence of chunk dictionaries to split into batches.
        
        Returns:
            Iterator[List[Dict[str, Any]]]: An iterator that yields lists of chunk dicts, each list containing up to `batch_size` items.
        """
        for i in range(0, len(chunks), self.batch_size):
            yield chunks[i:i + self.batch_size]
