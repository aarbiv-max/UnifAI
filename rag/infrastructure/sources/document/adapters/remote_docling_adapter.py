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
