# Hexagonal Architecture Implementation Guide

**Feature:** Shared Docling & Embedding Service Clients  
**Date:** February 4, 2026  
**Scope:** `global_utils/` and `rag/` directories

---

## Overview

This guide provides step-by-step instructions to refactor the docling and embedding clients to follow the hexagonal architecture pattern with proper separation of concerns:

- **Client Layer**: Pure HTTP transport (thin)
- **Service Layer**: Business logic, validation, error handling
- **Models Layer**: DTOs (Request/Response Pydantic models)
- **Exceptions Layer**: Custom domain exceptions
- **Ports Layer**: Abstract interfaces (ABCs)
- **Adapters Layer**: Concrete implementations that use the service layer
- **Factory Layer**: Creates adapters with proper dependency injection
- **Container Layer**: Wires dependencies as singletons

---

## Part 1: global_utils Changes

### Step 1.1: Create Docling Module Structure

Create the following directory structure:

```
global_utils/src/global_utils/docling/
├── __init__.py
├── client.py
├── service.py
├── models.py
└── exceptions.py
```

### Step 1.2: Create `global_utils/src/global_utils/docling/exceptions.py`

```python
"""Docling domain exceptions."""


class DoclingError(Exception):
    """Base exception for all docling-related errors."""
    pass


class DoclingConnectionError(DoclingError):
    """Raised when the docling service is unreachable."""
    pass


class DoclingProcessingError(DoclingError):
    """Raised when document processing fails."""
    pass


class DoclingValidationError(DoclingError):
    """Raised when input validation fails."""
    pass


class DoclingTimeoutError(DoclingError):
    """Raised when a request times out."""
    pass
```

### Step 1.3: Create `global_utils/src/global_utils/docling/models.py`

```python
"""Docling DTOs (Data Transfer Objects)."""

from typing import Dict, Any, Optional, List
from pydantic import AliasChoices, AliasPath, BaseModel, Field
from global_utils.validators import CoercedStr


class DoclingOptions(BaseModel):
    """Options for document conversion."""
    to_formats: List[str] = Field(default_factory=lambda: ["md", "text"])
    image_export_mode: Optional[str] = None
    pdf_backend: Optional[str] = None


class DoclingRequest(BaseModel):
    """Request model for docling conversion."""
    file_path: Optional[str] = None
    url: Optional[str] = None
    options: DoclingOptions = Field(default_factory=DoclingOptions)


class DoclingResponse(BaseModel):
    """
    Response model for docling conversion.
    
    Handles multiple response formats using AliasChoices:
    - Direct fields: markdown, text, content
    - Nested document: document.md_content, document.text_content
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
        return bool(
            (self.markdown and self.markdown.strip()) or 
            (self.text and self.text.strip())
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
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
```

### Step 1.4: Create `global_utils/src/global_utils/docling/client.py`

```python
"""
Docling HTTP Client - Pure transport layer.

This client handles only HTTP communication with the docling service.
Business logic, validation, and error transformation are in the service layer.
"""

import os
import logging
from typing import Dict, Any, Optional, List

import httpx

from global_utils.docling.exceptions import (
    DoclingConnectionError,
    DoclingTimeoutError,
)

logger = logging.getLogger(__name__)


class DoclingClient:
    """
    Pure HTTP client for docling service.
    
    Handles only transport concerns:
    - HTTP requests/responses
    - Connection management
    - Timeout handling
    
    Example:
        client = DoclingClient(
            base_url="http://docling-service:5001",
            timeout=300,
        )
        raw_response = client.post_file("/path/to/doc.pdf", options={...})
    """
    
    def __init__(
        self, 
        base_url: str,
        timeout: int = 300,
    ):
        """
        Initialize the HTTP client.
        
        Args:
            base_url: Base URL for the docling service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
        )
        logger.info(f"DoclingClient initialized: {self.base_url}, timeout={self.timeout}s")
    
    def post_file(
        self, 
        file_path: str, 
        to_formats: List[str],
        image_export_mode: Optional[str] = None,
        pdf_backend: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        POST a file to the docling service for conversion.
        
        Args:
            file_path: Path to the file to convert
            to_formats: List of output formats (e.g., ["md", "text"])
            image_export_mode: Mode for image export (e.g., "placeholder")
            pdf_backend: PDF parsing backend (e.g., "pypdfium2")
        
        Returns:
            Raw JSON response from the service
            
        Raises:
            DoclingConnectionError: If service is unreachable
            DoclingTimeoutError: If request times out
        """
        url = "/v1/convert/file"
        
        try:
            with open(file_path, 'rb') as f:
                files = {'files': (os.path.basename(file_path), f)}
                
                data = []
                for fmt in to_formats:
                    data.append(('to_formats', fmt))
                
                if image_export_mode:
                    data.append(('image_export_mode', image_export_mode))
                
                if pdf_backend:
                    data.append(('pdf_backend', pdf_backend))
                
                response = self._client.post(url, files=files, data=data)
                response.raise_for_status()
                return response.json()
                
        except httpx.ConnectError as e:
            raise DoclingConnectionError(f"Cannot connect to docling service: {e}")
        except httpx.TimeoutException as e:
            raise DoclingTimeoutError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise DoclingConnectionError(f"HTTP error {e.response.status_code}: {e}")
    
    def post_url(
        self, 
        document_url: str, 
        to_formats: List[str],
        image_export_mode: Optional[str] = None,
        pdf_backend: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        POST a URL to the docling service for conversion.
        
        Args:
            document_url: URL of the document to convert
            to_formats: List of output formats
            image_export_mode: Mode for image export
            pdf_backend: PDF parsing backend
        
        Returns:
            Raw JSON response from the service
            
        Raises:
            DoclingConnectionError: If service is unreachable
            DoclingTimeoutError: If request times out
        """
        url = "/v1/convert/source"
        
        try:
            payload = {
                "sources": [{"kind": "http", "url": document_url}],
                "to_formats": to_formats
            }
            
            if image_export_mode:
                payload["image_export_mode"] = image_export_mode
            
            if pdf_backend:
                payload["pdf_backend"] = pdf_backend
            
            response = self._client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json", "accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.ConnectError as e:
            raise DoclingConnectionError(f"Cannot connect to docling service: {e}")
        except httpx.TimeoutException as e:
            raise DoclingTimeoutError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise DoclingConnectionError(f"HTTP error {e.response.status_code}: {e}")
    
    def health_check(self) -> bool:
        """
        Check if the docling service is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self._client.get("/health", timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

### Step 1.5: Create `global_utils/src/global_utils/docling/service.py`

```python
"""
Docling Service - Business logic layer.

This service wraps the HTTP client and provides:
- Input validation
- Response parsing
- Error transformation
- Business logic for document processing
"""

import os
import logging
from typing import Optional

from global_utils.docling.client import DoclingClient
from global_utils.docling.models import DoclingResponse, DoclingOptions
from global_utils.docling.exceptions import (
    DoclingProcessingError,
    DoclingValidationError,
)

logger = logging.getLogger(__name__)


class DoclingService:
    """
    Business logic wrapper for docling operations.
    
    Provides:
    - File/URL validation
    - Response parsing into typed DTOs
    - Error handling and transformation
    
    Example:
        client = DoclingClient(base_url="http://docling:5001")
        service = DoclingService(client, image_export_mode="placeholder")
        response = service.process_file("/path/to/document.pdf")
        print(response.markdown)
    """
    
    def __init__(
        self,
        client: DoclingClient,
        image_export_mode: Optional[str] = None,
        pdf_backend: Optional[str] = None,
        default_formats: Optional[list] = None,
    ):
        """
        Initialize the service.
        
        Args:
            client: DoclingClient instance for HTTP communication
            image_export_mode: Default mode for image export (e.g., "placeholder")
            pdf_backend: Default PDF backend (e.g., "pypdfium2")
            default_formats: Default output formats (defaults to ["md", "text"])
        """
        self._client = client
        self.image_export_mode = image_export_mode
        self.pdf_backend = pdf_backend
        self.default_formats = default_formats or ["md", "text"]
        logger.info(
            f"DoclingService initialized: image_mode={image_export_mode}, "
            f"pdf_backend={pdf_backend}"
        )
    
    def process_file(
        self, 
        file_path: str, 
        to_formats: Optional[list] = None,
    ) -> DoclingResponse:
        """
        Process a local file through the docling service.
        
        Args:
            file_path: Path to the file to process
            to_formats: Output formats (uses default_formats if not specified)
        
        Returns:
            DoclingResponse with extracted content
            
        Raises:
            DoclingValidationError: If file doesn't exist or is invalid
            DoclingProcessingError: If processing fails
        """
        # Validate file exists
        if not os.path.exists(file_path):
            raise DoclingValidationError(f"File not found: {file_path}")
        
        formats = to_formats or self.default_formats
        
        try:
            logger.info(f"Processing file: {file_path}")
            raw_result = self._client.post_file(
                file_path=file_path,
                to_formats=formats,
                image_export_mode=self.image_export_mode,
                pdf_backend=self.pdf_backend,
            )
            
            response = DoclingResponse.model_validate(raw_result)
            
            if not response.has_content:
                raise DoclingProcessingError(
                    f"No content extracted from '{os.path.basename(file_path)}'"
                )
            
            logger.info(f"Successfully processed: {file_path}")
            return response
            
        except DoclingProcessingError:
            raise
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            raise DoclingProcessingError(
                f"Failed to process '{os.path.basename(file_path)}': {e}"
            )
    
    def process_url(
        self, 
        document_url: str, 
        to_formats: Optional[list] = None,
    ) -> DoclingResponse:
        """
        Process a document from URL through the docling service.
        
        Args:
            document_url: URL of the document to process
            to_formats: Output formats (uses default_formats if not specified)
        
        Returns:
            DoclingResponse with extracted content
            
        Raises:
            DoclingValidationError: If URL is invalid
            DoclingProcessingError: If processing fails
        """
        if not document_url:
            raise DoclingValidationError("Document URL cannot be empty")
        
        formats = to_formats or self.default_formats
        
        try:
            logger.info(f"Processing URL: {document_url}")
            raw_result = self._client.post_url(
                document_url=document_url,
                to_formats=formats,
                image_export_mode=self.image_export_mode,
                pdf_backend=self.pdf_backend,
            )
            
            response = DoclingResponse.model_validate(raw_result)
            
            if not response.has_content:
                raise DoclingProcessingError(
                    f"No content extracted from URL '{document_url}'"
                )
            
            logger.info(f"Successfully processed URL: {document_url}")
            return response
            
        except DoclingProcessingError:
            raise
        except Exception as e:
            logger.error(f"Error processing URL {document_url}: {e}")
            raise DoclingProcessingError(
                f"Failed to process URL '{document_url}': {e}"
            )
    
    def test_connection(self) -> bool:
        """
        Test if the docling service is accessible.
        
        Returns:
            True if service is healthy, False otherwise
        """
        return self._client.health_check()
```

### Step 1.6: Create `global_utils/src/global_utils/docling/__init__.py`

```python
"""
Docling module - Shared client library for document processing.

This module provides a client library for interacting with docling services,
designed for cross-project reusability (RAG, multi-agent, etc.).

Architecture:
    - client.py: Pure HTTP transport layer
    - service.py: Business logic, validation, error handling
    - models.py: Request/Response DTOs (Pydantic)
    - exceptions.py: Custom domain exceptions

Usage:
    from global_utils.docling import DoclingClient, DoclingService
    
    client = DoclingClient(base_url="http://docling:5001", timeout=300)
    service = DoclingService(client, image_export_mode="placeholder")
    
    response = service.process_file("/path/to/document.pdf")
    print(response.markdown)
"""

from global_utils.docling.client import DoclingClient
from global_utils.docling.service import DoclingService
from global_utils.docling.models import (
    DoclingOptions,
    DoclingRequest,
    DoclingResponse,
)
from global_utils.docling.exceptions import (
    DoclingError,
    DoclingConnectionError,
    DoclingProcessingError,
    DoclingValidationError,
    DoclingTimeoutError,
)

__all__ = [
    # Client & Service
    "DoclingClient",
    "DoclingService",
    # Models
    "DoclingOptions",
    "DoclingRequest",
    "DoclingResponse",
    # Exceptions
    "DoclingError",
    "DoclingConnectionError",
    "DoclingProcessingError",
    "DoclingValidationError",
    "DoclingTimeoutError",
]
```

### Step 1.7: Create Embedding Module Structure

Create the following directory structure:

```
global_utils/src/global_utils/embedding/
├── __init__.py
├── client.py
├── service.py
├── models.py
└── exceptions.py
```

### Step 1.8: Create `global_utils/src/global_utils/embedding/exceptions.py`

```python
"""Embedding domain exceptions."""


class EmbeddingError(Exception):
    """Base exception for all embedding-related errors."""
    pass


class EmbeddingConnectionError(EmbeddingError):
    """Raised when the embedding service is unreachable."""
    pass


class EmbeddingProcessingError(EmbeddingError):
    """Raised when embedding generation fails."""
    pass


class EmbeddingValidationError(EmbeddingError):
    """Raised when input validation fails."""
    pass


class EmbeddingTimeoutError(EmbeddingError):
    """Raised when a request times out."""
    pass
```

### Step 1.9: Create `global_utils/src/global_utils/embedding/models.py`

```python
"""Embedding DTOs (Data Transfer Objects)."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    """Request model for embedding generation."""
    texts: List[str]
    model: Optional[str] = None


class EmbeddingData(BaseModel):
    """Single embedding data item."""
    object: str = "embedding"
    index: int = 0
    embedding: List[float] = Field(default_factory=list)


class EmbeddingResponse(BaseModel):
    """
    Response model for embedding generation.
    
    Compatible with OpenAI embeddings API format.
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
    
    @property
    def embedding_count(self) -> int:
        """Get the number of embeddings in the response."""
        return len(self.data)
```

### Step 1.10: Create `global_utils/src/global_utils/embedding/client.py`

```python
"""
Embedding HTTP Client - Pure transport layer.

This client handles only HTTP communication with the embedding service.
Supports OpenAI-compatible embedding endpoints (like Text Embeddings Inference).
"""

import logging
from typing import Dict, Any, List

import httpx

from global_utils.embedding.exceptions import (
    EmbeddingConnectionError,
    EmbeddingTimeoutError,
)

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """
    Pure HTTP client for embedding service.
    
    Handles only transport concerns:
    - HTTP requests/responses
    - Connection management
    - Timeout handling
    
    Example:
        client = EmbeddingClient(
            base_url="http://embedding-service:5002",
            timeout=60,
        )
        raw_response = client.post_embeddings(["text1", "text2"], model="all-MiniLM-L6-v2")
    """
    
    def __init__(
        self, 
        base_url: str,
        timeout: int = 60,
    ):
        """
        Initialize the HTTP client.
        
        Args:
            base_url: Base URL for the embedding service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
        )
        logger.info(f"EmbeddingClient initialized: {self.base_url}, timeout={self.timeout}s")
    
    def post_embeddings(
        self, 
        texts: List[str], 
        model: str,
    ) -> Dict[str, Any]:
        """
        POST texts to the embedding service for embedding generation.
        
        Args:
            texts: List of text strings to embed
            model: Model name to use for embedding
        
        Returns:
            Raw JSON response from the service (OpenAI-compatible format)
            
        Raises:
            EmbeddingConnectionError: If service is unreachable
            EmbeddingTimeoutError: If request times out
        """
        url = "/v1/embeddings"
        
        try:
            payload = {
                "input": texts,
                "model": model
            }
            
            response = self._client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json", "accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.ConnectError as e:
            raise EmbeddingConnectionError(f"Cannot connect to embedding service: {e}")
        except httpx.TimeoutException as e:
            raise EmbeddingTimeoutError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            raise EmbeddingConnectionError(f"HTTP error {e.response.status_code}: {e}")
    
    def health_check(self) -> bool:
        """
        Check if the embedding service is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self._client.get("/health", timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def close(self):
        """Close the HTTP client."""
        self._client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

### Step 1.11: Create `global_utils/src/global_utils/embedding/service.py`

```python
"""
Embedding Service - Business logic layer.

This service wraps the HTTP client and provides:
- Input validation
- Response parsing
- Error transformation
- Batch processing logic
"""

import logging
from typing import List, Optional

from global_utils.embedding.client import EmbeddingClient
from global_utils.embedding.models import EmbeddingResponse
from global_utils.embedding.exceptions import (
    EmbeddingProcessingError,
    EmbeddingValidationError,
)

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Business logic wrapper for embedding operations.
    
    Provides:
    - Input validation
    - Response parsing into typed DTOs
    - Error handling and transformation
    - Batch processing
    
    Example:
        client = EmbeddingClient(base_url="http://embedding:5002")
        service = EmbeddingService(client, model_name="all-MiniLM-L6-v2")
        embeddings = service.generate_embeddings(["Hello", "World"])
    """
    
    def __init__(
        self,
        client: EmbeddingClient,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        """
        Initialize the service.
        
        Args:
            client: EmbeddingClient instance for HTTP communication
            model_name: Model name to use for embedding generation
        """
        self._client = client
        self.model_name = model_name
        logger.info(f"EmbeddingService initialized: model={model_name}")
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            List of embedding vectors (each vector is a list of floats)
            
        Raises:
            EmbeddingValidationError: If input is invalid
            EmbeddingProcessingError: If embedding generation fails
        """
        if not texts:
            raise EmbeddingValidationError("Texts list cannot be empty")
        
        try:
            logger.debug(f"Generating embeddings for {len(texts)} texts")
            raw_result = self._client.post_embeddings(
                texts=texts,
                model=self.model_name,
            )
            
            response = EmbeddingResponse.model_validate(raw_result)
            embeddings = response.extract_embeddings()
            
            if len(embeddings) != len(texts):
                logger.warning(
                    f"Expected {len(texts)} embeddings but got {len(embeddings)}"
                )
            
            logger.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings
            
        except EmbeddingProcessingError:
            raise
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise EmbeddingProcessingError(f"Failed to generate embeddings: {e}")
    
    def generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector as a list of floats
            
        Raises:
            EmbeddingValidationError: If text is empty
            EmbeddingProcessingError: If embedding generation fails
        """
        if not text:
            raise EmbeddingValidationError("Text cannot be empty")
        
        embeddings = self.generate_embeddings([text])
        if not embeddings:
            raise EmbeddingProcessingError("No embedding generated")
        
        return embeddings[0]
    
    def test_connection(self) -> bool:
        """
        Test if the embedding service is accessible.
        
        Returns:
            True if service is healthy, False otherwise
        """
        return self._client.health_check()
```

### Step 1.12: Create `global_utils/src/global_utils/embedding/__init__.py`

```python
"""
Embedding module - Shared client library for embedding generation.

This module provides a client library for interacting with embedding services,
designed for cross-project reusability (RAG, multi-agent, etc.).

Architecture:
    - client.py: Pure HTTP transport layer
    - service.py: Business logic, validation, error handling
    - models.py: Request/Response DTOs (Pydantic)
    - exceptions.py: Custom domain exceptions

Usage:
    from global_utils.embedding import EmbeddingClient, EmbeddingService
    
    client = EmbeddingClient(base_url="http://embedding:5002", timeout=60)
    service = EmbeddingService(client, model_name="all-MiniLM-L6-v2")
    
    embeddings = service.generate_embeddings(["Hello", "World"])
"""

from global_utils.embedding.client import EmbeddingClient
from global_utils.embedding.service import EmbeddingService
from global_utils.embedding.models import (
    EmbeddingRequest,
    EmbeddingData,
    EmbeddingResponse,
)
from global_utils.embedding.exceptions import (
    EmbeddingError,
    EmbeddingConnectionError,
    EmbeddingProcessingError,
    EmbeddingValidationError,
    EmbeddingTimeoutError,
)

__all__ = [
    # Client & Service
    "EmbeddingClient",
    "EmbeddingService",
    # Models
    "EmbeddingRequest",
    "EmbeddingData",
    "EmbeddingResponse",
    # Exceptions
    "EmbeddingError",
    "EmbeddingConnectionError",
    "EmbeddingProcessingError",
    "EmbeddingValidationError",
    "EmbeddingTimeoutError",
]
```

### Step 1.13: Update `global_utils/src/global_utils/__init__.py`

Add the new modules to the package exports:

```python
"""Global utilities package."""

from global_utils.docling import (
    DoclingClient,
    DoclingService,
    DoclingResponse,
    DoclingProcessingError,
)
from global_utils.embedding import (
    EmbeddingClient,
    EmbeddingService,
    EmbeddingResponse,
    EmbeddingProcessingError,
)

__all__ = [
    # Docling
    "DoclingClient",
    "DoclingService",
    "DoclingResponse",
    "DoclingProcessingError",
    # Embedding
    "EmbeddingClient",
    "EmbeddingService",
    "EmbeddingResponse",
    "EmbeddingProcessingError",
]
```

### Step 1.14: Delete Old Client Files

Remove the old flat client structure:

- Delete: `global_utils/src/global_utils/clients/docling_service_client.py`
- Delete: `global_utils/src/global_utils/clients/embedding_service_client.py`
- Delete: `global_utils/src/global_utils/clients/__init__.py`
- Delete: `global_utils/src/global_utils/clients/` directory

---

## Part 2: RAG Backend Changes

### Step 2.1: Create Port Interface for Document Conversion

Create `rag/core/connector/domain/document_converter.py`:

```python
"""Document converter port - domain interface for document conversion."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class DocumentConverterPort(ABC):
    """
    Abstract interface for document conversion.
    
    This port defines the contract for converting documents to text/markdown.
    Implementations can be local (docling library) or remote (HTTP service).
    """
    
    @abstractmethod
    def convert_file(self, file_path: str) -> Dict[str, Any]:
        """
        Convert a local file to text/markdown.
        
        Args:
            file_path: Path to the file to convert
            
        Returns:
            Dictionary with keys: text, markdown, metadata
            
        Raises:
            DocumentConversionError: If conversion fails
        """
        pass
    
    @abstractmethod
    def convert_url(self, document_url: str) -> Dict[str, Any]:
        """
        Convert a document from URL to text/markdown.
        
        Args:
            document_url: URL of the document to convert
            
        Returns:
            Dictionary with keys: text, markdown, metadata
            
        Raises:
            DocumentConversionError: If conversion fails
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if the converter is available.
        
        Returns:
            True if available, False otherwise
        """
        pass


class DocumentConversionError(Exception):
    """Raised when document conversion fails."""
    pass
```

### Step 2.2: Create Local Docling Adapter

Create `rag/infrastructure/sources/document/adapters/local_docling_adapter.py`:

```python
"""Local Docling Adapter - uses docling library directly."""

import os
import logging
from typing import Dict, Any

from docling.document_converter import DocumentConverter, InputFormat, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from pypdfium2 import PdfiumError

from core.connector.domain.document_converter import (
    DocumentConverterPort,
    DocumentConversionError,
)

logger = logging.getLogger(__name__)


class LocalDoclingAdapter(DocumentConverterPort):
    """
    Adapter that uses the local docling library for document conversion.
    
    This adapter loads the docling library and processes documents locally.
    Use when running in environments where the docling service is not available.
    """
    
    def __init__(self):
        """Initialize the local docling converter."""
        pdf_pipeline_options = PdfPipelineOptions(do_ocr=False)
        pdf_format_option = PdfFormatOption(
            pipeline_options=pdf_pipeline_options,
            backend=PyPdfiumDocumentBackend
        )
        self._converter = DocumentConverter(
            format_options={InputFormat.PDF: pdf_format_option}
        )
        logger.info("LocalDoclingAdapter initialized")
    
    def convert_file(self, file_path: str) -> Dict[str, Any]:
        """Convert a local file using docling library."""
        if not os.path.exists(file_path):
            raise DocumentConversionError(f"File not found: {file_path}")
        
        try:
            logger.info(f"Converting file locally: {file_path}")
            result = self._converter.convert(file_path)
            
            text_content = result.document.export_to_text()
            
            if not text_content or not text_content.strip():
                raise DocumentConversionError(
                    f"No content extracted from '{os.path.basename(file_path)}'"
                )
            
            return {
                "text": text_content,
                "markdown": result.document.export_to_markdown(),
                "metadata": self._extract_metadata(result),
            }
            
        except DocumentConversionError:
            raise
        except PdfiumError:
            raise DocumentConversionError(
                "The PDF appears to be corrupted or invalid."
            )
        except Exception as e:
            logger.error(f"Error converting file {file_path}: {e}")
            raise DocumentConversionError(str(e))
    
    def convert_url(self, document_url: str) -> Dict[str, Any]:
        """Convert a document from URL using docling library."""
        try:
            logger.info(f"Converting URL locally: {document_url}")
            result = self._converter.convert(document_url)
            
            text_content = result.document.export_to_text()
            
            if not text_content or not text_content.strip():
                raise DocumentConversionError(
                    f"No content extracted from URL '{document_url}'"
                )
            
            return {
                "text": text_content,
                "markdown": result.document.export_to_markdown(),
                "metadata": self._extract_metadata(result),
            }
            
        except DocumentConversionError:
            raise
        except PdfiumError:
            raise DocumentConversionError(
                "The PDF at the URL appears to be corrupted or invalid."
            )
        except Exception as e:
            logger.error(f"Error converting URL {document_url}: {e}")
            raise DocumentConversionError(str(e))
    
    def test_connection(self) -> bool:
        """Local adapter is always available."""
        return True
    
    def _extract_metadata(self, result) -> Dict[str, Any]:
        """Extract metadata from docling conversion result."""
        metadata = {}
        doc = result.document
        
        if hasattr(doc, "metadata") and doc.metadata:
            metadata.update(doc.metadata)
        
        metadata["title"] = doc.title if hasattr(doc, "title") else "Untitled"
        metadata["page_count"] = len(doc.pages) if hasattr(doc, "pages") else 1
        
        text = doc.export_to_text()
        metadata["character_count"] = len(text)
        metadata["word_count"] = len(text.split())
        
        return metadata
```

### Step 2.3: Create Remote Docling Adapter

Create `rag/infrastructure/sources/document/adapters/remote_docling_adapter.py`:

```python
"""Remote Docling Adapter - uses docling HTTP service."""

import os
import logging
from typing import Dict, Any

from global_utils.docling import DoclingService, DoclingProcessingError

from core.connector.domain.document_converter import (
    DocumentConverterPort,
    DocumentConversionError,
)

logger = logging.getLogger(__name__)


class RemoteDoclingAdapter(DocumentConverterPort):
    """
    Adapter that uses the remote docling service for document conversion.
    
    This adapter delegates to the DoclingService from global_utils.
    Use when running in environments where the docling service is available.
    """
    
    def __init__(self, docling_service: DoclingService):
        """
        Initialize with a DoclingService instance.
        
        Args:
            docling_service: Configured DoclingService for HTTP communication
        """
        self._service = docling_service
        logger.info("RemoteDoclingAdapter initialized")
    
    def convert_file(self, file_path: str) -> Dict[str, Any]:
        """Convert a local file using remote docling service."""
        try:
            logger.info(f"Converting file remotely: {file_path}")
            response = self._service.process_file(file_path)
            
            result = response.to_dict()
            result["metadata"] = self._build_metadata(response, file_path)
            
            return result
            
        except DoclingProcessingError as e:
            raise DocumentConversionError(str(e))
        except Exception as e:
            logger.error(f"Error converting file {file_path}: {e}")
            raise DocumentConversionError(str(e))
    
    def convert_url(self, document_url: str) -> Dict[str, Any]:
        """Convert a document from URL using remote docling service."""
        try:
            logger.info(f"Converting URL remotely: {document_url}")
            response = self._service.process_url(document_url)
            
            result = response.to_dict()
            result["metadata"] = self._build_metadata(response)
            
            return result
            
        except DoclingProcessingError as e:
            raise DocumentConversionError(str(e))
        except Exception as e:
            logger.error(f"Error converting URL {document_url}: {e}")
            raise DocumentConversionError(str(e))
    
    def test_connection(self) -> bool:
        """Test if remote docling service is available."""
        return self._service.test_connection()
    
    def _build_metadata(self, response, file_path: str = None) -> Dict[str, Any]:
        """Build metadata from response."""
        metadata = dict(response.metadata) if response.metadata else {}
        
        text = response.text or ""
        metadata["character_count"] = len(text)
        metadata["word_count"] = len(text.split())
        
        if "page_count" not in metadata and text:
            metadata["page_count"] = max(1, len(text) // 2000)
        
        if file_path:
            metadata["filename"] = os.path.basename(file_path)
        
        return metadata
```

### Step 2.4: Create Adapters Package Init

Create `rag/infrastructure/sources/document/adapters/__init__.py`:

```python
"""Document conversion adapters."""

from infrastructure.sources.document.adapters.local_docling_adapter import (
    LocalDoclingAdapter,
)
from infrastructure.sources.document.adapters.remote_docling_adapter import (
    RemoteDoclingAdapter,
)

__all__ = [
    "LocalDoclingAdapter",
    "RemoteDoclingAdapter",
]
```

### Step 2.5: Create Local Embedding Adapter

Create `rag/infrastructure/embedding/adapters/local_embedding_adapter.py`:

```python
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
```

### Step 2.6: Create Remote Embedding Adapter

Create `rag/infrastructure/embedding/adapters/remote_embedding_adapter.py`:

```python
"""Remote Embedding Adapter - uses embedding HTTP service."""

import logging
from typing import List

import numpy as np

from global_utils.embedding import EmbeddingService, EmbeddingProcessingError

from core.vector.domain.embedder import EmbeddingPort

logger = logging.getLogger(__name__)


class RemoteEmbeddingAdapter(EmbeddingPort):
    """
    Adapter that uses remote embedding service for embedding generation.
    
    This adapter delegates to the EmbeddingService from global_utils.
    Use when running in environments where the embedding service is available.
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        embedding_dim: int = 384,
    ):
        """
        Initialize with an EmbeddingService instance.
        
        Args:
            embedding_service: Configured EmbeddingService for HTTP communication
            embedding_dim: Dimension of the embeddings
        """
        self._service = embedding_service
        self._embedding_dim = embedding_dim
        logger.info(f"RemoteEmbeddingAdapter initialized: dim={embedding_dim}")
    
    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension."""
        return self._embedding_dim
    
    def encode_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Encode texts using remote embedding service."""
        if not texts:
            return []
        
        try:
            embeddings = self._service.generate_embeddings(texts)
            return [np.array(e) for e in embeddings]
        except EmbeddingProcessingError:
            raise
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise EmbeddingProcessingError(str(e))
    
    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text."""
        if not text:
            raise ValueError("Text cannot be empty")
        
        try:
            embedding = self._service.generate_single_embedding(text)
            return np.array(embedding)
        except EmbeddingProcessingError:
            raise
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise EmbeddingProcessingError(str(e))
    
    def test_connection(self) -> bool:
        """Test if remote embedding service is available."""
        return self._service.test_connection()
```

### Step 2.7: Create Embedding Adapters Package Init

Create `rag/infrastructure/embedding/adapters/__init__.py`:

```python
"""Embedding adapters."""

from infrastructure.embedding.adapters.local_embedding_adapter import (
    LocalEmbeddingAdapter,
)
from infrastructure.embedding.adapters.remote_embedding_adapter import (
    RemoteEmbeddingAdapter,
)

__all__ = [
    "LocalEmbeddingAdapter",
    "RemoteEmbeddingAdapter",
]
```

### Step 2.8: Update Embedding Port Interface

Update `rag/core/vector/domain/embedder.py`:

```python
"""Embedding generator port - domain interface for embedding generation."""

import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Iterator


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
```

### Step 2.9: Update Document Connector

Replace `rag/infrastructure/sources/document/connector.py`:

```python
"""
Document Connector - unified document processing adapter.

This connector uses a DocumentConverterPort for the actual conversion,
allowing seamless switching between local and remote implementations.
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional

from core.connector.domain.base import DataConnector
from core.connector.domain.document_converter import (
    DocumentConverterPort,
    DocumentConversionError,
)
from infrastructure.sources.document.config import DocConfigManager

logger = logging.getLogger(__name__)


class DocumentConnector(DataConnector):
    """
    Unified document connector using port-based architecture.
    
    The actual document conversion is delegated to a DocumentConverterPort,
    which can be either LocalDoclingAdapter or RemoteDoclingAdapter.
    """
    
    def __init__(
        self, 
        converter: DocumentConverterPort,
        config_manager: Optional[DocConfigManager] = None,
    ):
        """
        Initialize the document connector.
        
        Args:
            converter: DocumentConverterPort implementation (local or remote)
            config_manager: Configuration manager for document processing
        """
        if config_manager is None:
            config_manager = DocConfigManager()
            
        super().__init__(config_manager)
        
        self._converter = converter
        self._conversion_results: Dict[str, Any] = {}
        
        logger.info(
            f"DocumentConnector initialized with {type(converter).__name__}"
        )

    def authenticate(self) -> bool:
        """No authentication required for document processing."""
        return True
    
    def test_connection(self) -> bool:
        """Test if document processing is available."""
        return self._converter.test_connection()
    
    def _validate_document(self, document_path: str) -> float:
        """
        Validate document before processing.
        
        Args:
            document_path: Path to the document file
            
        Returns:
            File size in MB
        """
        if not os.path.exists(document_path):
            raise DocumentConversionError(f"Document not found: {document_path}")
            
        _, file_extension = os.path.splitext(document_path)
        supported_extensions = self._config_manager.get_config_value("supported_extensions")
        
        if file_extension.lower() not in supported_extensions:
            raise DocumentConversionError(
                f"Unsupported file extension: {file_extension}. "
                f"Supported types: {supported_extensions}"
            )

        file_size_mb = os.path.getsize(document_path) / (1024 * 1024)
        max_size_mb = self._config_manager.get_config_value("max_file_size_mb")

        if file_size_mb > max_size_mb:
            raise DocumentConversionError(
                f"File size ({file_size_mb:.2f} MB) exceeds maximum ({max_size_mb} MB)"
            )
        
        return file_size_mb

    def process_document(
        self, 
        document_path: str, 
        upload_by: str = "default",
    ) -> Optional[Dict[str, Any]]:
        """
        Process a document file and extract text and metadata.
        
        Args:
            document_path: Path to the document file
            upload_by: User who uploaded the document
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        file_size_mb = self._validate_document(document_path)
        
        logger.info(f"Processing document: {document_path}")
        
        result = self._converter.convert_file(document_path)
        self._conversion_results[document_path] = result
        
        document_data = {
            "text": result.get("text", ""),
            "markdown": result.get("markdown", ""),
            "path": document_path,
            "filename": os.path.basename(document_path),
        }
        
        if self._config_manager.get_config_value("include_metadata"):
            metadata = result.get("metadata", {})
            metadata["upload_by"] = upload_by
            metadata["file_size"] = f"{file_size_mb:.2f} MB"
            document_data["metadata"] = metadata
            
        logger.info(f"Document processed: {document_path}")
        return document_data
    
    def process_documents(self, document_paths: List[str]) -> List[Dict[str, Any]]:
        """Process multiple documents."""
        logger.info(f"Processing batch of {len(document_paths)} documents")
        
        results = []
        failed_count = 0
        
        for doc_path in document_paths:
            try:
                result = self.process_document(doc_path)
                if result:
                    results.append(result)
            except DocumentConversionError as e:
                logger.error(f"Failed to process {doc_path}: {e}")
                failed_count += 1
                
        logger.info(
            f"Batch complete. Processed {len(results)}/{len(document_paths)}. "
            f"Failed: {failed_count}"
        )
        return results

    def process_document_url(
        self, 
        document_url: str, 
        upload_by: str = "default",
    ) -> Optional[Dict[str, Any]]:
        """Process a document from a URL."""
        logger.info(f"Processing document URL: {document_url}")
        
        result = self._converter.convert_url(document_url)
        self._conversion_results[document_url] = result
        
        document_data = {
            "text": result.get("text", ""),
            "markdown": result.get("markdown", ""),
            "url": document_url,
        }
        
        if self._config_manager.get_config_value("include_metadata"):
            metadata = result.get("metadata", {})
            metadata["upload_by"] = upload_by
            document_data["metadata"] = metadata
            
        logger.info(f"Document URL processed: {document_url}")
        return document_data
    
    def get_document_structure(self, document_path: str) -> Optional[Dict[str, Any]]:
        """Get the hierarchical structure of a document."""
        if document_path not in self._conversion_results:
            logger.warning(f"Document not processed yet: {document_path}")
            return None
            
        result = self._conversion_results[document_path]
        structure = {"title": "Untitled", "sections": []}
        
        markdown = result.get("markdown", "")
        if markdown:
            header_pattern = r"^(#{1,6})\s+(.*)$"
            for line in markdown.split("\n"):
                match = re.match(header_pattern, line)
                if match:
                    structure["sections"].append({
                        "title": match.group(2).strip(),
                        "level": len(match.group(1)),
                        "text": ""
                    })
        
        return structure
```

### Step 2.10: Create Default Embedding Generator Implementation

Create `rag/infrastructure/embedding/embedding_generator.py`:

```python
"""Default EmbeddingGenerator implementation."""

import logging
from typing import Dict, List, Any

from core.vector.domain.embedder import EmbeddingGenerator, EmbeddingPort

logger = logging.getLogger(__name__)


class DefaultEmbeddingGenerator(EmbeddingGenerator):
    """
    Default implementation of EmbeddingGenerator.
    
    Uses an EmbeddingPort for encoding and adds logging.
    """
    
    def __init__(self, port: EmbeddingPort, batch_size: int = 32):
        """Initialize with an embedding port."""
        super().__init__(port, batch_size)
        logger.info(
            f"DefaultEmbeddingGenerator initialized: "
            f"dim={self.embedding_dim}, batch_size={batch_size}"
        )
    
    def generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate embeddings with logging."""
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        result = super().generate_embeddings(chunks)
        logger.info(f"Generated {len(result)} embeddings")
        return result
```

### Step 2.11: Update Factories

Replace `rag/bootstrap/factories.py`:

```python
"""Factory classes for creating adapter instances."""

import os
import logging
from typing import Dict, Any

import torch

from config.app_config import AppConfig
from core.vector.domain.embedder import EmbeddingGenerator
from core.vector.domain.repository import VectorRepository
from core.connector.domain.base import DataConnector
from core.connector.domain.document_converter import DocumentConverterPort

logger = logging.getLogger(__name__)

device = "cuda" if torch.cuda.is_available() else "cpu"
app_config = AppConfig.get_instance()


class DocumentConverterFactory:
    """Factory for creating document converter port instances."""
    
    @staticmethod
    def create_local() -> DocumentConverterPort:
        """Create a local docling adapter."""
        from infrastructure.sources.document.adapters import LocalDoclingAdapter
        return LocalDoclingAdapter()
    
    @staticmethod
    def create_remote(
        base_url: str,
        timeout: int = 300,
        image_export_mode: str = "placeholder",
        pdf_backend: str = "pypdfium2",
    ) -> DocumentConverterPort:
        """Create a remote docling adapter."""
        from global_utils.docling import DoclingClient, DoclingService
        from infrastructure.sources.document.adapters import RemoteDoclingAdapter
        
        client = DoclingClient(base_url=base_url, timeout=timeout)
        service = DoclingService(
            client=client,
            image_export_mode=image_export_mode,
            pdf_backend=pdf_backend,
        )
        return RemoteDoclingAdapter(docling_service=service)


class DocumentConnectorFactory:
    """Factory for creating document connector instances."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> DataConnector:
        """
        Create a document connector instance.
        
        Args:
            config: Configuration dict with keys:
                - type: "local" or "remote"
                - service_url: URL (for remote)
                - timeout: Timeout in seconds (for remote)
                - config_manager: Optional DocConfigManager
        """
        from infrastructure.sources.document.connector import DocumentConnector
        from infrastructure.sources.document.config import DocConfigManager
        
        connector_type = config.get("type", "local")
        config_manager = config.get("config_manager") or DocConfigManager()
        
        if connector_type == "local":
            converter = DocumentConverterFactory.create_local()
        elif connector_type == "remote":
            converter = DocumentConverterFactory.create_remote(
                base_url=config.get("service_url"),
                timeout=config.get("timeout", 300),
            )
        else:
            raise ValueError(f"Unknown connector type: {connector_type}")
        
        return DocumentConnector(
            converter=converter,
            config_manager=config_manager,
        )


class EmbeddingPortFactory:
    """Factory for creating embedding port instances."""
    
    @staticmethod
    def create_local(
        model_name: str = "all-MiniLM-L6-v2",
        device_name: str = None,
    ):
        """Create a local embedding adapter."""
        from infrastructure.embedding.adapters import LocalEmbeddingAdapter
        return LocalEmbeddingAdapter(
            model_name=model_name,
            device=device_name or device,
        )
    
    @staticmethod
    def create_remote(
        base_url: str,
        timeout: int = 60,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim: int = 384,
    ):
        """Create a remote embedding adapter."""
        from global_utils.embedding import EmbeddingClient, EmbeddingService
        from infrastructure.embedding.adapters import RemoteEmbeddingAdapter
        
        client = EmbeddingClient(base_url=base_url, timeout=timeout)
        service = EmbeddingService(client=client, model_name=model_name)
        return RemoteEmbeddingAdapter(
            embedding_service=service,
            embedding_dim=embedding_dim,
        )


class EmbeddingGeneratorFactory:
    """Factory for creating embedding generator instances."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> EmbeddingGenerator:
        """
        Create an embedding generator instance.
        
        Args:
            config: Configuration dict with keys:
                - type: "local" or "remote"
                - model_name: Model name
                - batch_size: Batch size
                - device: Device (for local)
                - service_url: URL (for remote)
                - timeout: Timeout (for remote)
                - embedding_dim: Dimension (for remote)
        """
        from infrastructure.embedding.embedding_generator import DefaultEmbeddingGenerator
        
        generator_type = config.get("type", "local")
        batch_size = config.get("batch_size", 32)
        
        if generator_type == "local":
            port = EmbeddingPortFactory.create_local(
                model_name=config.get("model_name", "all-MiniLM-L6-v2"),
                device_name=config.get("device"),
            )
        elif generator_type == "remote":
            port = EmbeddingPortFactory.create_remote(
                base_url=config.get("service_url"),
                timeout=config.get("timeout", 60),
                model_name=config.get("model_name", "sentence-transformers/all-MiniLM-L6-v2"),
                embedding_dim=config.get("embedding_dim", 384),
            )
        else:
            raise ValueError(f"Unknown generator type: {generator_type}")
        
        return DefaultEmbeddingGenerator(port=port, batch_size=batch_size)


class VectorRepositoryFactory:
    """Factory for creating vector repository instances."""
    
    @staticmethod
    def create(config: Dict[str, Any]) -> VectorRepository:
        """Create a vector repository instance."""
        from infrastructure.qdrant.qdrant_vector_repository import QdrantVectorRepository
        
        storage_type = config.get("type", "qdrant")
        
        if storage_type == "qdrant":
            return QdrantVectorRepository(
                collection_name=config.get("collection_name", "default_collection"),
                embedding_dim=config.get("embedding_dim", 384),
                url=app_config.qdrant_ip or config.get("url"),
                port=int(app_config.qdrant_port) or config.get("port"),
                grpc_port=config.get("grpc_port"),
                api_key=config.get("api_key"),
                on_disk=config.get("on_disk", True),
                replication_factor=config.get("replication_factor", 1),
                write_consistency_factor=config.get("write_consistency_factor", 1),
            )
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")
```

### Step 2.12: Update App Container

Update the relevant sections in `rag/bootstrap/app_container.py`:

```python
# ══════════════════════════════════════════════════════════════════════════════
# CONNECTORS (Infrastructure layer - data source adapters)
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def document_connector():
    """
    Document connector for PDF and other document formats.
    
    Uses local docling library by default.
    Set USE_REMOTE_DOCLING=true to use the remote docling service.
    """
    from bootstrap.factories import DocumentConnectorFactory
    from config.app_config import AppConfig
    
    config = AppConfig.get_instance()
    
    if config.use_remote_docling:
        return DocumentConnectorFactory.create({
            "type": "remote",
            "service_url": config.docling_service_url,
            "timeout": config.docling_service_timeout,
        })
    else:
        return DocumentConnectorFactory.create({"type": "local"})


# ══════════════════════════════════════════════════════════════════════════════
# EMBEDDING & VECTOR COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def embedding_generator():
    """
    Shared embedding generator.
    
    Uses local SentenceTransformer by default.
    Set USE_REMOTE_EMBEDDING=true to use the remote embedding service.
    """
    from bootstrap.factories import EmbeddingGeneratorFactory
    from config.app_config import AppConfig
    
    config = AppConfig.get_instance()
    
    if config.use_remote_embedding:
        return EmbeddingGeneratorFactory.create({
            "type": "remote",
            "service_url": config.embedding_service_url,
            "timeout": config.embedding_service_timeout,
            "model_name": config.embedding_service_model,
            "embedding_dim": 384,
        })
    else:
        return EmbeddingGeneratorFactory.create({"type": "local"})
```

### Step 2.13: Delete Old Files

Remove the following deprecated files:

- Delete: `rag/infrastructure/embedding/sentence_transformer_embedder.py`
- Delete: `rag/infrastructure/clients/` directory (if exists and empty)

---

## Part 3: Configuration

### Step 3.1: Ensure App Config Has Required Fields

Verify `rag/config/app_config.py` contains:

```python
# External Docling Service Configuration
docling_service_url: str = "http://docling-service:5001"
docling_service_timeout: int = 300

# External Embedding Service Configuration
embedding_service_url: str = "http://embedding-service:5002"
embedding_service_timeout: int = 60
embedding_service_model: str = "sentence-transformers/all-MiniLM-L6-v2"

# Feature flags to switch between local and remote adapters
use_remote_docling: bool = False
use_remote_embedding: bool = False
```

### Step 3.2: Add httpx Dependency

Add to `global_utils/pyproject.toml` or `requirements.txt`:

```
httpx>=0.25.0
```

---

## Part 4: Final Directory Structure

After completing all steps, the structure should be:

```
global_utils/src/global_utils/
├── __init__.py
├── validators.py
├── config/
│   └── config.py
├── docling/
│   ├── __init__.py
│   ├── client.py
│   ├── service.py
│   ├── models.py
│   └── exceptions.py
└── embedding/
    ├── __init__.py
    ├── client.py
    ├── service.py
    ├── models.py
    └── exceptions.py

rag/
├── bootstrap/
│   ├── app_container.py
│   └── factories.py
├── config/
│   └── app_config.py
├── core/
│   ├── connector/
│   │   └── domain/
│   │       ├── base.py
│   │       └── document_converter.py  (NEW)
│   └── vector/
│       └── domain/
│           └── embedder.py  (UPDATED)
└── infrastructure/
    ├── embedding/
    │   ├── embedding_generator.py  (NEW)
    │   └── adapters/
    │       ├── __init__.py
    │       ├── local_embedding_adapter.py
    │       └── remote_embedding_adapter.py
    └── sources/
        └── document/
            ├── connector.py  (UPDATED)
            ├── config.py
            ├── chunker.py
            └── adapters/
                ├── __init__.py
                ├── local_docling_adapter.py
                └── remote_docling_adapter.py
```

---

## Part 5: Verification Checklist

After implementation, verify:

- [ ] `global_utils.docling` module imports work
- [ ] `global_utils.embedding` module imports work
- [ ] `DocumentConnectorFactory.create({"type": "local"})` works
- [ ] `DocumentConnectorFactory.create({"type": "remote", ...})` works
- [ ] `EmbeddingGeneratorFactory.create({"type": "local"})` works
- [ ] `EmbeddingGeneratorFactory.create({"type": "remote", ...})` works
- [ ] `document_connector()` returns correct adapter based on config
- [ ] `embedding_generator()` returns correct adapter based on config
- [ ] All existing tests pass
- [ ] No circular imports

---

## Summary

This implementation follows the hexagonal architecture pattern:

1. **Ports (Interfaces)**: `DocumentConverterPort`, `EmbeddingPort`
2. **Adapters**: Local and Remote implementations for each port
3. **Factories**: Create adapters with proper dependency injection
4. **Container**: Wires dependencies based on configuration
5. **Shared Clients**: Reusable HTTP clients in `global_utils`

The architecture enables:
- Easy switching between local and remote modes via config flags
- Cross-project reuse of HTTP clients (RAG, multi-agent, etc.)
- Clear separation of concerns (transport, business logic, domain)
- Testability through port-based design
