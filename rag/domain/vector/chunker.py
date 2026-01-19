from abc import ABC, abstractmethod 
from typing import Dict, List, Any

class ContentChunker(ABC):
    """
    Abstract base class for content chunking strategies.
    
    This class defines the common interface and shared functionality
    for implementing different chunking approaches for various data sources.
    """
    
    def __init__(self, max_tokens_per_chunk: int = 500, overlap_tokens: int = 50):
        """
        Create a ContentChunker with token sizing and overlap configuration.
        
        Parameters:
            max_tokens_per_chunk (int): Maximum tokens allowed in a single chunk. Defaults to 500.
            overlap_tokens (int): Number of tokens to overlap between adjacent chunks. Defaults to 50.
        """
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.overlap_tokens = overlap_tokens
        self._chunks = []
        
    @property
    def chunks(self) -> List[Dict[str, Any]]:
        """
        Get the list of generated content chunks.
        
        Returns:
            List[Dict[str, Any]]: The list of chunk dictionaries stored by the chunker, in creation order.
        """
        return self._chunks
    
    @property
    def chunk_count(self) -> int:
        """
        Number of generated chunks.
        
        Returns:
            chunk_count (int): The count of chunks currently stored in the chunker.
        """
        return len(self._chunks)
    
    @abstractmethod
    def chunk_content(self, content: Any) -> List[Dict[str, Any]]:
        """
        Split input content into logical chunks according to the implemented strategy.
        
        Parameters:
            content (Any): Source content to split; format and structure are implementation-specific.
        
        Returns:
            List[Dict[str, Any]]: A list of chunk dictionaries. Each dictionary contains the chunk's content (e.g., under a 'content' key) and associated metadata (e.g., under a 'metadata' key).
        """
        pass
    
    @abstractmethod
    def estimate_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in the given text.
        
        Parameters:
            text (str): Input text whose token count will be estimated.
        
        Returns:
            int: Estimated number of tokens in the input text.
        """
        pass
