"""Base log parser utility for extracting information from log lines."""
import re
from datetime import datetime
from typing import Optional, Tuple

from domain.pipeline.model import PipelineStatus


class LogParser:
    """
    Utility class for parsing log lines and extracting relevant information.
    
    This class provides methods to extract statistics, status updates, and other
    useful data from log entries.
    """
    
    @staticmethod
    def parse_log_line(log_line: str) -> Tuple[datetime, str, str, str]:
        """
        Parse a log line into timestamp, module name, log level, and message.
        
        If the line matches "YYYY-MM-DD HH:MM:SS,mmm - module - LEVEL - message", returns the parsed values.
        If the line does not match, returns the current datetime, module "unknown", log level "INFO", and the original log line as the message.
        
        Returns:
            (timestamp, module, log_level, message): A tuple where `timestamp` is a datetime, `module` and `log_level` are strings, and `message` is the log message. On parse failure, `timestamp` is the current time, `module` is "unknown", `log_level` is "INFO", and `message` is the original `log_line`.
        """
        # Example log format: 2025-05-04 03:19:30,185 - data_pipeline - INFO - Making API request to Slack endpoint: auth.test
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (\w+) - (.*)'
        match = re.match(pattern, log_line)
        
        if match:
            timestamp_str, module, level, message = match.groups()
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
            return timestamp, module, level, message
        
        # Fallback for logs that don't match the expected pattern
        return datetime.now(), "unknown", "INFO", log_line
    
    @staticmethod
    def extract_chunk_count(log_line: str) -> Optional[int]:
        """
        Extracts the total chunk count from a log line.
        
        Searches for messages of the form "Completed chunking with <N> total chunks generated" and returns the integer count.
        
        Parameters:
            log_line (str): A single log entry to inspect.
        
        Returns:
            int: The extracted chunk count if present, `None` otherwise.
        """
        pattern = r'Completed chunking with (\d+) total chunks generated'
        match = re.search(pattern, log_line)
        if match:
            return int(match.group(1))
        return None
    
    @staticmethod
    def extract_embedding_count(log_line: str) -> Optional[int]:
        """
        Extracts the number of embeddings reported as stored in a log line.
        
        Parameters:
            log_line (str): Log entry to search for an embedding count.
        
        Returns:
            int | None: The extracted number of stored embeddings if present, otherwise None.
        """
        pattern = r'Stored (\d+) embeddings'
        match = re.search(pattern, log_line)
        if match:
            return int(match.group(1))
            
        return None
    
    @staticmethod
    def extract_pipeline_status(log_line: str) -> Optional[PipelineStatus]:
        """
        Infers a pipeline status from a single log line.
        
        @returns `PipelineStatus.DONE` if the line indicates embeddings were stored, `PipelineStatus.FAILED` if the line indicates an error or failure, `None` otherwise.
        """
        # Examples to detect completion
        if "Stored" in log_line and "embeddings" in log_line:
            return PipelineStatus.DONE
        
        # Examples to detect errors
        if "ERROR" in log_line or "Failed" in log_line:
            return PipelineStatus.FAILED
            
        return None
