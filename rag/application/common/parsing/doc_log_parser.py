"""Document-specific log parser for extracting document pipeline information."""
import re
from typing import Optional

from domain.pipeline.model import PipelineStatus
from .log_parser import LogParser


class DocLogParser(LogParser):
    """
    Parser for document-specific log entries.
    
    This class extends the base LogParser with methods specific to document processing logs.
    """
    
    @staticmethod
    def extract_doc_id(log_line: str) -> Optional[str]:
        """
        Extracts a document identifier from a log line.
        
        Matches common filename formats (e.g., .pdf, .docx, .txt) or explicit alphanumeric IDs containing letters, digits, hyphens, or underscores when present in the log text.
        
        Returns:
            The extracted document ID string if found, otherwise None.
        """
        # Try to find document ID in "Processing document" or similar log entries
        patterns = [
            r'Processing document: ([^/\s]+\.pdf|[^/\s]+\.docx|[^/\s]+\.txt)$',  # For direct filename references
            r'Processing document: .*?/([^/]+\.(pdf|docx|txt))$',  # For path-based references
            r'Processing document: .* \(ID: ([A-Za-z0-9_-]+)\)',  # For explicit ID references
            r'document ([^/\s]+\.(pdf|docx|txt)) in',  # For references in processing time logs
            r'Successfully processed document: ([^/\s]+\.(pdf|docx|txt))'  # For success logs
        ]
        
        for pattern in patterns:
            match = re.search(pattern, log_line)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def extract_api_endpoint(log_line: str) -> Optional[str]:
        """
        Extracts an API endpoint URL from a log line.
        
        Searches for full HTTP(S) request URLs and generic "API request to" references and returns the first match.
        
        Returns:
            The extracted endpoint URL as a string, or None if no endpoint is present.
        """
        # Pattern for httpx logs
        http_pattern = r'HTTP Request: (GET|POST|PUT|DELETE|PATCH) (http[s]?://[^\s"]+)'
        match = re.search(http_pattern, log_line)
        if match:
            return match.group(2)
        
        # Pattern for other API calls
        api_pattern = r'API request to ([^\s]+)'
        match = re.search(api_pattern, log_line)
        if match:
            return match.group(1)
            
        return None
    
    @staticmethod
    def extract_chunk_count(log_line: str) -> Optional[int]:
        """
        Extracts the total number of chunks reported in a log line.
        
        Returns:
            The extracted chunk count as an `int` if a count is found, `None` otherwise.
        """
        patterns = [
            r'Completed chunking with (\d+) total chunks generated'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, log_line)
            if match:
                return int(match.group(1))
        
        return None
    
    @staticmethod
    def extract_embedding_count(log_line: str) -> Optional[int]:
        """
        Extracts the number of embeddings reported in a log line.
        
        Returns:
            int: Embedding count if found, None otherwise.
        """
        patterns = [
            r'Starting embedding generation for (\d+) chunks',
            r'Storing (\d+) embeddings in',
            r'Stored (\d+) embeddings in'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, log_line)
            if match:
                return int(match.group(1))
        
        return None
    
    @staticmethod
    def extract_processing_status(log_line: str) -> Optional[PipelineStatus]:
        """
        Determine the pipeline processing status indicated by a log line.
        
        Returns:
            PipelineStatus or None: One of PipelineStatus.ACTIVE, PipelineStatus.DONE, or PipelineStatus.FAILED when the line contains a corresponding indicator, or `None` if no status is present.
        """
        if re.search(r'Starting to process', log_line):
            return PipelineStatus.ACTIVE
        elif re.search(r'Successfully processed document|Document processed successfully', log_line):
            return PipelineStatus.DONE
        elif re.search(r'Failed to process|Error processing document', log_line):
            return PipelineStatus.FAILED
        
        return None
