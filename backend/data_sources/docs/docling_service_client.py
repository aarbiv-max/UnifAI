"""
Docling Service Client

This module provides a client for interacting with the external docling service API.
It replaces the internal docling library usage with HTTP calls to the service.
"""

import os
import requests
from typing import Dict, Any, Optional
from pydantic import AliasChoices, AliasPath, BaseModel, Field
from shared.logger import logger
from .pdf_chunker_strategy import DoclingProcessingError
from config.app_config import AppConfig
from global_utils.validators import CoercedStr


class DoclingResponse(BaseModel):
    """
    Pydantic model for parsing docling service responses.
    
    Handles multiple response formats using AliasChoices:
    - Direct fields: markdown, text, content
    - Nested document: document.md_content, document.text_content
    - Metadata at root level
    """
    markdown: CoercedStr = Field(
        default="",
        validation_alias=AliasChoices(
            "markdown",
            "md_content",
            AliasPath("document", "md_content"),
        )
    )
    text: CoercedStr = Field(
        default="",
        validation_alias=AliasChoices(
            "text",
            "text_content",
            "content",
            AliasPath("document", "text_content"),
        )
    )
    filename: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "filename",
            AliasPath("document", "filename"),
        )
    )
    # Handle metadata from both root level and nested document.metadata paths
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices(
            "metadata",
            AliasPath("document", "metadata"),
        )
    )
    
    @property
    def has_content(self) -> bool:
        """Check if the response contains any extractable content."""
        return bool((self.markdown and self.markdown.strip()) or 
                    (self.text and self.text.strip()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format expected by the rest of the application."""
        result = {}
        if self.markdown:
            result["markdown"] = self.markdown
        if self.text:
            result["text"] = self.text
        if self.filename:
            result["filename"] = self.filename
        if self.metadata:
            result["metadata"] = self.metadata
        return result


class DoclingServiceClient:
    """
    Client for interacting with the external docling service.
    
    This client handles document conversion by making HTTP requests to the docling service
    instead of using the internal docling library.
    """
    
    def __init__(self, timeout: Optional[int] = None):
        """
        Initialize the docling service client.
        
        Args:
            timeout: Request timeout in seconds. If not provided, reads from 
                    app_config.docling_service_timeout (default: 300).
        """
        self.app_config = AppConfig.get_instance()
        self.base_url = self.app_config.docling_service_url.rstrip('/')
        self.timeout = timeout if timeout is not None else self.app_config.docling_service_timeout
        logger.info(f"DoclingServiceClient initialized with base URL: {self.base_url}, timeout: {self.timeout}s")
    
    def convert_file(
        self, 
        file_path: str, 
        to_formats: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Convert a local file using the docling service.
        
        Args:
            file_path: Path to the local file to convert
            to_formats: List of formats to request (e.g., ["md", "text", "json"]).
                       Defaults to ["md", "text"] if not provided.
        
        Returns:
            Dictionary containing converted content with keys like "markdown", "text", etc.
        
        Raises:
            DoclingProcessingError: If conversion fails or returns no content
            FileNotFoundError: If the file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if to_formats is None:
            to_formats = ["md", "text"]
        
        url = f"{self.base_url}/v1/convert/file"
        
        try:
            logger.info(f"Converting file {file_path} via docling service")
            
            # Prepare multipart form data
            # The API expects multiple to_formats parameters
            # We need to send them as separate form fields with the same name
            with open(file_path, 'rb') as f:
                files = {'files': (os.path.basename(file_path), f)}
                
                # For multiple values with the same key, we need to use a list of tuples
                # But requests doesn't support this directly, so we'll use a workaround
                # by creating a custom payload or using data parameter with tuples
                form_data = []
                for fmt in to_formats:
                    form_data.append(('to_formats', fmt))
                
                response = requests.post(
                    url,
                    files=files,
                    data=form_data,
                    timeout=self.timeout
                )
            
            response.raise_for_status()
            result = response.json()
            
            # Parse response using Pydantic model
            parsed_response = DoclingResponse.model_validate(result)
            
            if not parsed_response.has_content:
                logger.error(f"Docling service returned no extractable content. Response: {result}")
                raise DoclingProcessingError(
                    f"Docling service was unable to process the provided document "
                    f"'{os.path.basename(file_path)}'. No text or markdown content found in response."
                )
            
            logger.info(f"Successfully converted file {file_path} via docling service")
            return parsed_response.to_dict()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling docling service for file {file_path}: {str(e)}")
            raise DoclingProcessingError(
                f"Failed to convert document '{os.path.basename(file_path)}' via docling service: {str(e)}"
            )
        except DoclingProcessingError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error converting file {file_path}: {str(e)}")
            raise DoclingProcessingError(
                f"Unexpected error processing document '{os.path.basename(file_path)}': {str(e)}"
            )
    
    def convert_url(
        self, 
        document_url: str, 
        to_formats: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Convert a document from a URL using the docling service.
        
        Args:
            document_url: URL of the document to convert
            to_formats: List of formats to request (e.g., ["md", "text", "json"]).
                       Defaults to ["md", "text"] if not provided.
        
        Returns:
            Dictionary containing converted content with keys like "markdown", "text", etc.
        
        Raises:
            DoclingProcessingError: If conversion fails or returns no content
        """
        if to_formats is None:
            to_formats = ["md", "text"]
        
        url = f"{self.base_url}/v1/convert/source"
        
        try:
            logger.info(f"Converting document from URL {document_url} via docling service")
            
            payload = {
                "sources": [{"kind": "http", "url": document_url}],
                "to_formats": to_formats
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
            parsed_response = DoclingResponse.model_validate(result)
            
            if not parsed_response.has_content:
                logger.error(f"Docling service returned no extractable content. Response: {result}")
                raise DoclingProcessingError(
                    f"Docling service was unable to process the document from URL '{document_url}'. "
                    f"No text or markdown content found in response."
                )
            
            logger.info(f"Successfully converted document from URL {document_url} via docling service")
            return parsed_response.to_dict()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling docling service for URL {document_url}: {str(e)}")
            raise DoclingProcessingError(
                f"Failed to convert document from URL '{document_url}' via docling service: {str(e)}"
            )
        except DoclingProcessingError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error converting URL {document_url}: {str(e)}")
            raise DoclingProcessingError(
                f"Unexpected error processing document from URL '{document_url}': {str(e)}"
            )
    
    def test_connection(self) -> bool:
        """
        Test if the docling service is accessible.
        
        Returns:
            True if the service is accessible, False otherwise
        """
        try:
            # Try to access the health endpoint if available, or just check base URL
            health_url = f"{self.base_url}/health"
            response = requests.get(health_url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Could not connect to docling service at {self.base_url}: {str(e)}")
            return False
