"""
Embedding Service Client

This module provides a client for interacting with external embedding service APIs.
It supports OpenAI-compatible embedding endpoints (like Text Embeddings Inference).

This client is placed in global_utils for cross-project reusability.
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EmbeddingResponse(BaseModel):
    """
    Pydantic model for parsing embedding service responses.
    
    Handles OpenAI-compatible response format from Text Embeddings Inference.
    """
    object: str = Field(default="list")
    data: List[Dict[str, Any]] = Field(default_factory=list)
    model: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    
    def extract_embeddings(self) -> List[List[float]]:
        """Extract embedding vectors from the response."""
        embeddings = []
        for item in self.data:
            if "embedding" in item:
                embeddings.append(item["embedding"])
        return embeddings


class EmbeddingServiceError(Exception):
    """Exception raised when embedding service operations fail."""
    pass


class EmbeddingServiceClient:
    """
    Client for interacting with external embedding services.
    
    This client handles embedding generation by making HTTP requests to an
    OpenAI-compatible embedding service API instead of using local models.
    
    Example:
        client = EmbeddingServiceClient(
            base_url="http://embedding-service:5002",
            timeout=60,
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        embeddings = client.generate_embeddings(["Hello world", "Test text"])
    """
    
    def __init__(
        self, 
        base_url: str,
        timeout: Optional[int] = None, 
        model_name: Optional[str] = None
    ):
        """
        Initialize the embedding service client.
        
        Args:
            base_url: Base URL for the embedding service.
            timeout: Request timeout in seconds. Defaults to 60.
            model_name: Model name to use. Defaults to "sentence-transformers/all-MiniLM-L6-v2". 
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout if timeout is not None else 60
        self.model_name = model_name or 'sentence-transformers/all-MiniLM-L6-v2'
        logger.info(
            f"EmbeddingServiceClient initialized with base URL: {self.base_url}, "
            f"timeout: {self.timeout}s, model: {self.model_name}"
        )
    
    def generate_embeddings(
        self, 
        texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using the embedding service.
        
        Args:
            texts: List of text strings to generate embeddings for
        
        Returns:
            List of embedding vectors (each vector is a list of floats)
        
        Raises:
            ValueError: If texts list is empty
            EmbeddingServiceError: If the embedding generation fails
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")
        
        url = f"{self.base_url}/v1/embeddings"
        
        try:
            logger.debug(f"Generating embeddings for {len(texts)} texts via embedding service")
            
            payload = {
                "input": texts,
                "model": self.model_name
            }
            
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json", "accept": "application/json"},
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            parsed_response = EmbeddingResponse.model_validate(result)
            
            embeddings = parsed_response.extract_embeddings()
            
            if len(embeddings) != len(texts):
                logger.warning(
                    f"Expected {len(texts)} embeddings but got {len(embeddings)}. "
                    f"Some texts may have failed to generate embeddings."
                )
            
            logger.debug(f"Successfully generated {len(embeddings)} embeddings via embedding service")
            return embeddings
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling embedding service: {str(e)}")
            raise EmbeddingServiceError(
                f"Failed to generate embeddings via embedding service: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error generating embeddings: {str(e)}")
            raise EmbeddingServiceError(
                f"Unexpected error processing embeddings: {str(e)}"
            )
    
    def generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to generate embedding for
            
        Returns:
            Embedding vector as a list of floats
            
        Raises:
            ValueError: If text is empty
            EmbeddingServiceError: If the embedding generation fails
        """
        if not text:
            raise ValueError("Text cannot be empty")
        
        embeddings = self.generate_embeddings([text])
        if not embeddings:
            raise EmbeddingServiceError("No embedding generated for text")
        
        return embeddings[0]
    
    def test_connection(self) -> bool:
        """
        Test if the embedding service is accessible.
        
        Returns:
            True if the service is accessible, False otherwise
        """
        try:
            health_url = f"{self.base_url}/health"
            response = requests.get(health_url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Could not connect to embedding service at {self.base_url}: {str(e)}")
            return False
