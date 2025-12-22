"""
Embedding Service Client

This module provides a client for interacting with the external embedding service API.
It replaces the internal SentenceTransformer library usage with HTTP calls to the service.
"""

import requests
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from shared.logger import logger
from config.app_config import AppConfig
import numpy as np


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
        """
        Extract embedding vectors from the response.
        
        Returns:
            List of embedding vectors (each vector is a list of floats)
        """
        embeddings = []
        for item in self.data:
            if "embedding" in item:
                embeddings.append(item["embedding"])
        return embeddings


class EmbeddingServiceClient:
    """
    Client for interacting with the external embedding service.
    
    This client handles embedding generation by making HTTP requests to the embedding service
    instead of using the internal SentenceTransformer library.
    """
    
    def __init__(self, timeout: Optional[int] = None, model_name: Optional[str] = None):
        """
        Initialize the embedding service client.
        
        Args:
            timeout: Request timeout in seconds. If not provided, reads from 
                    app_config.embedding_service_timeout (default: 60).
            model_name: Model name to use. If not provided, uses default from config
                       or "sentence-transformers/all-MiniLM-L6-v2". 
                       Note: OpenAI-compatible API requires model name in requests,
                       but if your service only serves one model, this can be any value.
        """
        self.app_config = AppConfig.get_instance()
        self.base_url = self.app_config.embedding_service_url.rstrip('/')
        self.timeout = timeout if timeout is not None else getattr(
            self.app_config, 'embedding_service_timeout', 60
        )
        # Model name is required by OpenAI API format, but if service only serves one model,
        # it can be any value (service will use its configured model)
        self.model_name = model_name or getattr(
            self.app_config, 'embedding_service_model', 'sentence-transformers/all-MiniLM-L6-v2'
        )
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
            requests.exceptions.RequestException: If the API call fails
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")
        
        url = f"{self.base_url}/v1/embeddings"
        
        try:
            logger.debug(f"Generating embeddings for {len(texts)} texts via embedding service")
            
            payload = {
                "input": texts,
                "model": self.model_name  # Required by OpenAI API format
            }
            
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json", "accept": "application/json"},
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Parse response using Pydantic model
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
            raise ValueError(
                f"Failed to generate embeddings via embedding service: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error generating embeddings: {str(e)}")
            raise ValueError(
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
        """
        if not text:
            raise ValueError("Text cannot be empty")
        
        embeddings = self.generate_embeddings([text])
        if not embeddings:
            raise ValueError("No embedding generated for text")
        
        return embeddings[0]
    
    def test_connection(self) -> bool:
        """
        Test if the embedding service is accessible.
        
        Returns:
            True if the service is accessible, False otherwise
        """
        try:
            # Try to access the health endpoint
            health_url = f"{self.base_url}/health"
            response = requests.get(health_url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Could not connect to embedding service at {self.base_url}: {str(e)}")
            return False

