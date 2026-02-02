"""
Document Connector

This module provides a unified document connector that can work in two modes:
- Local mode: Uses the docling library to process documents locally
- Remote mode: Uses an external docling service via HTTP

The mode is determined by whether a service_client is injected at construction time.
This decision is made in the bootstrap layer (factory/app_container), not here.
"""

import os
import re
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from pathlib import Path
from shared.logger import logger
from core.connector.domain.base import DataConnector
from infrastructure.sources.document.config import DocConfigManager
from infrastructure.sources.document.chunker import DoclingProcessingError

if TYPE_CHECKING:
    from global_utils.clients import DoclingServiceClient


class DoclingProcessingError(Exception):
    """Exception raised when docling processing fails."""
    pass

class DocumentConnector(DataConnector):
    """
    Unified document connector supporting both local and remote modes.
    
    Local mode (service_client=None):
        Uses the docling library to process documents locally.
        Loads the document converter on initialization.
    
    Remote mode (service_client=DoclingServiceClient):
        Uses an external docling service via HTTP requests.
        No local docling library is loaded.
    
    The mode is determined by dependency injection - the factory/container
    decides which mode to use based on configuration.
    """
    
    def __init__(
        self, 
        config_manager: Optional[DocConfigManager] = None,
        service_client: Optional["DoclingServiceClient"] = None,
    ):
        """
        Initialize the document connector.
        
        Args:
            config_manager: Configuration manager for document processing
            service_client: Optional DoclingServiceClient for remote mode.
                           If provided, uses remote docling service.
                           If None, loads local docling library.
        """
        if config_manager is None:
            config_manager = DocConfigManager()
            
        super().__init__(config_manager)
        
        self._service_client = service_client
        self._conversion_results: Dict[str, Any] = {}
        
        if service_client:
            # Remote mode - no local docling needed
            self._converter = None
            logger.info("DocumentConnector initialized in REMOTE mode")
        else:
            # Local mode - initialize docling converter
            from docling.document_converter import DocumentConverter, InputFormat, PdfFormatOption
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
            
            pdf_pipeline_options = PdfPipelineOptions(do_ocr=False)
            pdf_format_option = PdfFormatOption(
                pipeline_options=pdf_pipeline_options,
                backend=PyPdfiumDocumentBackend
            )
            self._converter = DocumentConverter(
                format_options={InputFormat.PDF: pdf_format_option}
            )
            logger.info("DocumentConnector initialized in LOCAL mode")

    @property
    def is_remote(self) -> bool:
        """Check if the connector is using remote mode."""
        return self._service_client is not None
    
    def authenticate(self) -> bool:
        """
        No authentication required for document processing.
        
        Returns:
            True as no authentication is needed
        """
        mode = "remote" if self.is_remote else "local"
        logger.info(f"Document connector ({mode} mode) does not require authentication")
        return True
    
    def test_connection(self) -> bool:
        """
        Test if document processing is available.
        
        Returns:
            True if document processing capabilities are available
        """
        if self._service_client:
            return self._service_client.test_connection()
        return True
    
    def _validate_document(self, document_path: str) -> float:
        """
        Validate document before processing.
        
        Args:
            document_path: Path to the document file
            
        Returns:
            File size in MB
            
        Raises:
            DoclingProcessingError: If validation fails
        """
        # Validate the file exists
        if not os.path.exists(document_path):
            logger.error(f"Document not found: {document_path}")
            raise DoclingProcessingError(f"Document not found: {document_path}")
            
        # Validate file extension
        _, file_extension = os.path.splitext(document_path)
        supported_extensions = self._config_manager.get_config_value("supported_extensions")
        
        if file_extension.lower() not in supported_extensions:
            logger.error(f"Unsupported file extension: {file_extension}. Supported types: {supported_extensions}")
            raise DoclingProcessingError(
                f"Unsupported file extension: {file_extension}. Supported types: {supported_extensions}"
            )

        # Check file size
        file_size_mb = os.path.getsize(document_path) / (1024 * 1024)
        max_size_mb = self._config_manager.get_config_value("max_file_size_mb")

        if file_size_mb > max_size_mb:
            logger.error(f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb} MB)")
            raise DoclingProcessingError(
                f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb} MB)"
            )
        
        return file_size_mb

    def _convert_document_local(self, document_path: str) -> Dict[str, Any]:
        """
        Convert document using local docling library.
        
        Args:
            document_path: Path to the document
            
        Returns:
            Dictionary with text, markdown, and conversion result
        """
        from docling.document_converter import ConversionResult
        from pypdfium2 import PdfiumError
        
        try:
            logger.info(f"Using default docling conversion parameters (custom options not supported)")
            result = self._converter.convert(document_path)
            
            text_content = result.document.export_to_text()
            
            if not text_content or not text_content.strip():
                logger.error(f"Docling failed to extract text content from document: {document_path}")
                raise DoclingProcessingError(
                    f"Docling was unable to process the provided document "
                    f"'{os.path.basename(document_path)}'. Failed to extract text content from the document."
                )
            
            return {
                "text": text_content,
                "markdown": result.document.export_to_markdown(),
                "_conversion_result": result,  # Keep for metadata extraction
            }
        except DoclingProcessingError:
            raise
        except PdfiumError:
            raise DoclingProcessingError(
                "The PDF appears to be corrupted or invalid. Please upload a valid PDF."
            )
        except Exception as e:
            logger.error(f"Error processing document {document_path}: {str(e)}")
            raise DoclingProcessingError(str(e))

    def _convert_document_remote(self, document_path: str) -> Dict[str, Any]:
        """
        Convert document using remote docling service.
        
        Args:
            document_path: Path to the document
            
        Returns:
            Dictionary with text and markdown
        """
        from global_utils.clients import DoclingProcessingError as RemoteDoclingError
        
        try:
            result = self._service_client.convert_file(document_path, to_formats=["md", "text"])
            return result
        except RemoteDoclingError:
            raise DoclingProcessingError(str(RemoteDoclingError))
        except Exception as e:
            logger.error(f"Error processing document {document_path}: {str(e)}")
            raise DoclingProcessingError(str(e))

    def process_document(self, document_path: str, upload_by: str = "default") -> Optional[Dict[str, Any]]:
        """
        Process a document file and extract text and metadata.
        
        Args:
            document_path: Path to the document file
            upload_by: User who uploaded the document
            
        Returns:
            Dictionary containing extracted text and metadata, or None if processing failed
        """
        # Validate document
        file_size_mb = self._validate_document(document_path)
        
        mode_str = "remote service" if self.is_remote else "local docling"
        logger.info(f"Processing document via {mode_str}: {document_path}")
        
        try:
            # Convert using appropriate backend
            if self._service_client:
                result = self._convert_document_remote(document_path)
            else:
                result = self._convert_document_local(document_path)
            
            # Store the conversion result for future reference
            self._conversion_results[document_path] = result
            
            # Build document data
            document_data = {
                "text": result.get("text", ""),
                "markdown": result.get("markdown", ""),
                "path": document_path,
                "filename": os.path.basename(document_path),
            }
            
            # Add metadata if requested
            if self._config_manager.get_config_value("include_metadata"):
                document_data["metadata"] = self._extract_metadata(result, upload_by, file_size_mb)
                
            logger.info(f"Document processed successfully via {mode_str}: {document_path}")
            return document_data
            
        except DoclingProcessingError:
            raise
        except Exception as e:
            logger.error(f"Error processing document {document_path}: {str(e)}")
            raise DoclingProcessingError(str(e))
    
    def process_documents(self, document_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Process multiple documents.
        
        Args:
            document_paths: List of paths to document files
            
        Returns:
            List of processed document data
        """
        mode_str = "remote service" if self.is_remote else "local docling"
        logger.info(f"Processing batch of {len(document_paths)} documents via {mode_str}")
        
        results = []
        failed_count = 0
        
        for doc_path in document_paths:
            try:
                result = self.process_document(doc_path)
                if result:
                    results.append(result)
            except DoclingProcessingError as e:
                logger.error(f"Failed to process document {doc_path}: {str(e)}")
                failed_count += 1
                
        logger.info(
            f"Batch processing complete. Processed {len(results)} out of "
            f"{len(document_paths)} documents. Failed: {failed_count}"
        )
        return results
    
    def _convert_url_local(self, document_url: str) -> Dict[str, Any]:
        """
        Convert URL using local docling library.
        
        Args:
            document_url: URL of the document
            
        Returns:
            Dictionary with text, markdown, and conversion result
        """
        from pypdfium2 import PdfiumError
        
        try:
            logger.info(f"Using default docling conversion parameters (custom options not supported)")
            result = self._converter.convert(document_url)
            
            text_content = result.document.export_to_text()
            
            if not text_content or not text_content.strip():
                logger.error(f"Docling failed to extract text content from document URL: {document_url}")
                raise DoclingProcessingError(
                    f"Docling was unable to process the provided document from URL '{document_url}'. "
                    f"Failed to extract text content from the document."
                )
            
            return {
                "text": text_content,
                "markdown": result.document.export_to_markdown(),
                "_conversion_result": result,
            }
        except DoclingProcessingError:
            raise
        except PdfiumError:
            raise DoclingProcessingError(
                "The PDF at the provided URL appears to be corrupted or invalid. "
                "Please try another file or re-upload it."
            )
        except Exception as e:
            logger.error(f"Error processing document from URL {document_url}: {str(e)}")
            raise DoclingProcessingError(str(e))

    def _convert_url_remote(self, document_url: str) -> Dict[str, Any]:
        """
        Convert URL using remote docling service.
        
        Args:
            document_url: URL of the document
            
        Returns:
            Dictionary with text and markdown
        """
        try:
            result = self._service_client.convert_url(document_url, to_formats=["md", "text"])
            return result
        except Exception as e:
            logger.error(f"Error processing document from URL {document_url}: {str(e)}")
            raise DoclingProcessingError(str(e))

    def process_document_url(self, document_url: str, upload_by: str = "default") -> Optional[Dict[str, Any]]:
        """
        Process a document from a URL.
        
        Args:
            document_url: URL of the document
            upload_by: User who initiated the processing
            
        Returns:
            Dictionary containing extracted text and metadata, or None if processing failed
        """
        mode_str = "remote service" if self.is_remote else "local docling"
        logger.info(f"Processing document from URL via {mode_str}: {document_url}")
        
        try:
            # Convert using appropriate backend
            if self._service_client:
                result = self._convert_url_remote(document_url)
            else:
                result = self._convert_url_local(document_url)
            
            # Store the conversion result for future reference
            self._conversion_results[document_url] = result
            
            # Build document data
            document_data = {
                "text": result.get("text", ""),
                "markdown": result.get("markdown", ""),
                "url": document_url,
            }
            
            # Add metadata if requested
            if self._config_manager.get_config_value("include_metadata"):
                document_data["metadata"] = self._extract_metadata(result, upload_by, 0)
                
            logger.info(f"Document from URL processed successfully via {mode_str}: {document_url}")
            return document_data
            
        except DoclingProcessingError:
            raise
        except Exception as e:
            logger.error(f"Error processing document from URL {document_url}: {str(e)}")
            raise DoclingProcessingError(str(e))
    
    def _extract_metadata(
        self, 
        conversion_result: Dict[str, Any], 
        upload_by: str = "default", 
        file_size: float = 0,
    ) -> Dict[str, Any]:
        """
        Extract metadata from a conversion result.
        
        Handles both local (ConversionResult) and remote (Dict) formats.
        
        Args:
            conversion_result: The document conversion result
            upload_by: User who uploaded/processed the document
            file_size: File size in MB
            
        Returns:
            Dictionary containing document metadata
        """
        metadata = {}
        
        try:
            # Check if this is a local conversion result (has _conversion_result key)
            if "_conversion_result" in conversion_result:
                # Local mode - extract from ConversionResult object
                result = conversion_result["_conversion_result"]
                doc = result.document
                
                # Extract basic document metadata
                if hasattr(doc, "metadata") and doc.metadata:
                    metadata.update(doc.metadata)

                # Extract title
                metadata["title"] = doc.title if hasattr(doc, "title") else "Untitled"

                # Extract page count
                metadata["page_count"] = len(doc.pages) if hasattr(doc, "pages") else 1
                
                # Extract content statistics
                text = doc.export_to_text()
                metadata["character_count"] = len(text)
                metadata["word_count"] = len(text.split())
                
                # Extract table information if available
                if hasattr(result, "tables") and result.tables:
                    metadata["table_count"] = len(result.tables)
                    
                # Extract image information if available
                if hasattr(result, "images") and result.images:
                    metadata["image_count"] = len(result.images)
            else:
                # Remote mode - extract from Dict
                if "metadata" in conversion_result and isinstance(conversion_result["metadata"], dict):
                    metadata.update(conversion_result["metadata"])
                
                # Calculate stats from text
                text = conversion_result.get("text", "")
                if text:
                    metadata["character_count"] = len(text)
                    metadata["word_count"] = len(text.split())
                else:
                    metadata["character_count"] = 0
                    metadata["word_count"] = 0
                
                # Estimate page count if not provided
                if "page_count" not in metadata:
                    if text:
                        estimated_pages = max(1, len(text) // 2000)
                        metadata["page_count"] = estimated_pages
                    else:
                        metadata["page_count"] = 0
            
            # Common metadata
            metadata["upload_by"] = upload_by
            metadata["file_size"] = f"{file_size:.2f} MB" if file_size > 0 else "Unknown size"
                
        except Exception as e:
            logger.warning(f"Error extracting metadata: {str(e)}")
            
        return metadata
    
    def get_document_structure(self, document_path: str) -> Optional[Dict[str, Any]]:
        """
        Get the hierarchical structure of a document.
        
        Args:
            document_path: Path to the document
            
        Returns:
            Dictionary representing the document structure, or None if not available
        """
        if document_path not in self._conversion_results:
            logger.warning(f"Document not processed yet: {document_path}")
            return None
            
        try:
            result = self._conversion_results[document_path]
            structure = {
                "title": "Untitled",
                "sections": []
            }
            
            # Check if this is a local conversion result
            if "_conversion_result" in result:
                # Local mode - use docling's structure API
                conversion_result = result["_conversion_result"]
                structure["title"] = (
                    conversion_result.document.title 
                    if hasattr(conversion_result.document, "title") 
                    else "Untitled"
                )
                
                if hasattr(conversion_result.document, "sections"):
                    for section in conversion_result.document.sections:
                        section_data = {
                            "title": section.title,
                            "level": section.level if hasattr(section, "level") else 1,
                            "text": section.text if hasattr(section, "text") else "",
                        }
                        structure["sections"].append(section_data)
            else:
                # Remote mode - parse markdown headers
                markdown = result.get("markdown", "")
                if markdown:
                    header_pattern = r"^(#{1,6})\s+(.*)$"
                    for line in markdown.split("\n"):
                        match = re.match(header_pattern, line)
                        if match:
                            level = len(match.group(1))
                            title = match.group(2).strip()
                            structure["sections"].append({
                                "title": title,
                                "level": level,
                                "text": ""
                            })
            
            return structure
            
        except Exception as e:
            logger.error(f"Error extracting document structure: {str(e)}")
            return None
