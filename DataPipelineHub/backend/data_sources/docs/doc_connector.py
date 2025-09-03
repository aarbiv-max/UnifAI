import os
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path
from shared.logger import logger
from utils.data_connector import DataConnector
from .doc_config_manager import DocConfigManager
from .pdf_chunker_strategy import DoclingProcessingError
from config.app_config import AppConfig

class DocumentConnector(DataConnector):
    """
    Document connector for processing PDF and other document formats.
    
    Handles extraction of text and metadata from documents using docling.
    """
    
    def __init__(self, config_manager: Optional[DocConfigManager] = None):
        """
        Initialize the document connector.
        
        Args:
            config_manager: Configuration manager for document processing
        """
        if config_manager is None:
            config_manager = DocConfigManager()
            
        super().__init__(config_manager)
        
        # Initialize docling endpoint configuration
        self._app_config = AppConfig()

        # Try to get docling service URL from environment variables (set by Kubernetes)
        # Priority: K8s service discovery > external address > default localhost
        docling_ip = os.environ.get('DOCLING_IP')
        docling_port = os.environ.get('DOCLING_PORT')
        docling_ext_addr = os.environ.get('DOCLING_EXT_ADDR')

        if docling_ip and docling_port:
            # Use Kubernetes service discovery
            self._docling_base_url = f"http://{docling_ip}:{docling_port}"
        elif docling_ext_addr and docling_port:
            # Use external address from load balancer
            self._docling_base_url = f"http://{docling_ext_addr}:{docling_port}"
        else:
            # Fallback to configured URL (for local development)
            self._docling_base_url = self._app_config.docling_endpoint_url

        self._docling_api_version = self._app_config.docling_api_version
        self._docling_timeout = self._app_config.docling_timeout
        
        # Storage for conversion results
        self._conversion_results: Dict[str, Dict[str, Any]] = {}
        logger.info(f"DocumentConnector initialized with endpoint: {self._docling_base_url}")
    
    def authenticate(self) -> bool:
        """
        No authentication required for local document processing.
        
        Returns:
            True as no authentication is needed
        """
        logger.info("Document connector does not require authentication")
        return True
    
    def test_connection(self) -> bool:
        """
        Test if docling endpoint is available and working.
        
        Returns:
            True if docling endpoint is accessible
        """
        try:
            # Test endpoint health
            health_url = f"{self._docling_base_url}/health"
            response = requests.get(health_url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Docling endpoint health check failed: {str(e)}")
            return False
    
    def process_document(self, document_path: str, upload_by: str = "default") -> Optional[Dict[str, Any]]:
        """
        Process a document file and extract text and metadata.
        
        Args:
            document_path: Path to the document file
            
        Returns:
            Dictionary containing extracted text and metadata, or None if processing failed
        """
        # Validate the file exists
        if not os.path.exists(document_path):
            logger.error(f"Document not found: {document_path}")
            return None
            
        # Validate file extension
        _, file_extension = os.path.splitext(document_path)
        supported_extensions = self._config_manager.get_config_value("supported_extensions")
        
        if file_extension.lower() not in supported_extensions:
            logger.error(f"Unsupported file extension: {file_extension}. Supported types: {supported_extensions}")
            return None

        # Check file size
        file_size_mb = os.path.getsize(document_path) / (1024 * 1024)
        max_size_mb = self._config_manager.get_config_value("max_file_size_mb")

        if file_size_mb > max_size_mb:
            logger.error(f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb} MB)")
            return None
            
        try:
            logger.info(f"Processing document via endpoint: {document_path}")
            
            # Process the document with docling endpoint
            result = self._convert_document_via_endpoint(document_path)
            
            # Store the conversion result for future reference
            self._conversion_results[document_path] = result
            
            # Extract text and metadata from the endpoint response
            text_content = result.get("text", "")
            markdown_content = result.get("markdown", "")
            
            # Validate that docling extracted content
            if not text_content or not text_content.strip():
                logger.error(f"Docling endpoint failed to extract text content from document: {document_path}")
                raise DoclingProcessingError(f"Docling was unable to process the provided document '{os.path.basename(document_path)}'. Failed to extract text content from the document.")
       
            document_data = {
                "text": text_content,
                "markdown": markdown_content,
                "path": document_path,
                "filename": os.path.basename(document_path),
            }
            
            # Add metadata if requested
            if self._config_manager.get_config_value("include_metadata"):
                document_data["metadata"] = self._extract_metadata_from_response(result, upload_by, file_size_mb)
                
            logger.info(f"Document processed successfully via endpoint: {document_path}")
            return document_data
            
        except DoclingProcessingError:
            raise
        except Exception as e:
            logger.error(f"Error processing document {document_path}: {str(e)}")
            return None
    
    def process_documents(self, document_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Process multiple documents.
        
        Args:
            document_paths: List of paths to document files
            
        Returns:
            List of processed document data
        """
        logger.info(f"Processing batch of {len(document_paths)} documents")
        results = []
        
        for doc_path in document_paths:
            result = self.process_document(doc_path)
            if result:
                results.append(result)
                
        logger.info(f"Batch processing complete. Processed {len(results)} out of {len(document_paths)} documents")
        return results
    
    def process_document_url(self, document_url: str) -> Optional[Dict[str, Any]]:
        """
        Process a document from a URL.
        
        Args:
            document_url: URL of the document
            
        Returns:
            Dictionary containing extracted text and metadata, or None if processing failed
        """
        try:
            logger.info(f"Processing document from URL via endpoint: {document_url}")
            
            # Process the document with docling endpoint
            result = self._convert_document_url_via_endpoint(document_url)
            
            # Store the conversion result for future reference
            self._conversion_results[document_url] = result
            
            # Extract text and metadata from the endpoint response
            text_content = result.get("text", "")
            markdown_content = result.get("markdown", "")
            
            # Validate that docling extracted meaningful content
            if not text_content or not text_content.strip():
                logger.error(f"Docling endpoint failed to extract text content from document URL: {document_url}")
                raise DoclingProcessingError(f"Docling was unable to process the provided document from URL '{document_url}'. Failed to extract text content from the document.")
                        
            document_data = {
                "text": text_content,
                "markdown": markdown_content,
                "url": document_url,
            }
            
            # Add metadata if requested
            if self._config_manager.get_config_value("include_metadata"):
                document_data["metadata"] = self._extract_metadata_from_response(result)
                
            logger.info(f"Document from URL processed successfully via endpoint: {document_url}")
            return document_data
            
        except DoclingProcessingError:
            raise
        except Exception as e:
            logger.error(f"Error processing document from URL {document_url}: {str(e)}")
            return None
    
    def _convert_document_via_endpoint(self, document_path: str) -> Dict[str, Any]:
        """
        Convert a document file using the docling endpoint.
        
        Args:
            document_path: Path to the document file
            
        Returns:
            Dictionary containing conversion result
        """
        convert_url = f"{self._docling_base_url}/{self._docling_api_version}/convert/source"
        
        try:
            # Prepare the file for upload
            with open(document_path, 'rb') as file:
                files = {'file': (os.path.basename(document_path), file, 'application/octet-stream')}
                
                # Make the API request
                response = requests.post(
                    convert_url,
                    files=files,
                    timeout=self._docling_timeout
                )
                
                if response.status_code != 200:
                    raise Exception(f"Docling endpoint returned status {response.status_code}: {response.text}")
                
                result = response.json()
                
                # Extract text and markdown from the response
                # The exact structure depends on docling endpoint API response format
                return {
                    "text": result.get("text", ""),
                    "markdown": result.get("markdown", ""),
                    "metadata": result.get("metadata", {}),
                    "raw_response": result
                }
                
        except Exception as e:
            logger.error(f"Error calling docling endpoint for file {document_path}: {str(e)}")
            raise
    
    def _convert_document_url_via_endpoint(self, document_url: str) -> Dict[str, Any]:
        """
        Convert a document from URL using the docling endpoint.
        
        Args:
            document_url: URL of the document
            
        Returns:
            Dictionary containing conversion result
        """
        convert_url = f"{self._docling_base_url}/{self._docling_api_version}/convert/source"
        
        try:
            # Prepare the request payload for URL conversion
            payload = {
                "http_sources": [{"url": document_url}]
            }
            
            # Make the API request
            response = requests.post(
                convert_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self._docling_timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"Docling endpoint returned status {response.status_code}: {response.text}")
            
            result = response.json()
            
            # Extract text and markdown from the response
            return {
                "text": result.get("text", ""),
                "markdown": result.get("markdown", ""),
                "metadata": result.get("metadata", {}),
                "raw_response": result
            }
            
        except Exception as e:
            logger.error(f"Error calling docling endpoint for URL {document_url}: {str(e)}")
            raise
    
    def _extract_metadata_from_response(self, response_data: Dict[str, Any], upload_by="default", file_size=0) -> Dict[str, Any]:
        """
        Extract metadata from a docling endpoint response.
        
        Args:
            response_data: The response data from docling endpoint
            upload_by: User who uploaded the document
            file_size: File size in MB
            
        Returns:
            Dictionary containing document metadata
        """
        metadata = {}
        
        try:
            # Extract metadata from the endpoint response
            raw_metadata = response_data.get("metadata", {})
            if raw_metadata:
                metadata.update(raw_metadata)

            # Extract title
            metadata["title"] = raw_metadata.get("title", "Untitled")

            # Extract uploader
            metadata["upload_by"] = upload_by
            
            # Extract file size
            metadata["file_size"] = f"{file_size:.2f} MB" if file_size > 0 else "Unknown size"
                
            # Extract structural information from response
            metadata["page_count"] = raw_metadata.get("page_count", 1)
            
            # Extract content statistics
            text = response_data.get("text", "")
            metadata["character_count"] = len(text)
            metadata["word_count"] = len(text.split())
            
            # Extract table and image information if available
            metadata["table_count"] = raw_metadata.get("table_count", 0)
            metadata["image_count"] = raw_metadata.get("image_count", 0)
                
        except Exception as e:
            logger.warning(f"Error extracting metadata from response: {str(e)}")
            
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
            raw_metadata = result.get("metadata", {})
            
            structure = {
                "title": raw_metadata.get("title", "Untitled"),
                "sections": []
            }
            
            # Extract sections and subsections if available from the endpoint response
            sections = raw_metadata.get("sections", [])
            for section in sections:
                section_data = {
                    "title": section.get("title", ""),
                    "level": section.get("level", 1),
                    "text": section.get("text", ""),
                }
                structure["sections"].append(section_data)
            
            return structure
            
        except Exception as e:
            logger.error(f"Error extracting document structure: {str(e)}")
            return None