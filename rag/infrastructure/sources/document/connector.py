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
