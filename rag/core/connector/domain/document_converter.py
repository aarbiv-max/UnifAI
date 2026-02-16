"""Document converter port - domain interface for document conversion."""

from abc import ABC, abstractmethod
from typing import Dict, Any


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
