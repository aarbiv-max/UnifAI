"""Slack-specific log parser for extracting Slack pipeline information."""
import re
from typing import Optional

from .log_parser import LogParser


class SlackLogParser(LogParser):
    """
    Parser for Slack-specific log entries.
    
    This class extends the base LogParser with methods specific to Slack processing logs.
    """
    
    @staticmethod
    def extract_slack_channel_id(log_line: str) -> Optional[str]:
        """
        Extracts a Slack channel ID from a log line.
        
        Returns:
            channel_id (str | None): The captured channel ID if present, `None` otherwise.
        """
        pattern = r'ID: ([A-Z0-9]+)'
        match = re.search(pattern, log_line)
        if match:
            return match.group(1)
        return None
    
    @staticmethod
    def extract_api_endpoint(log_line: str) -> Optional[str]:
        """
        Extracts a Slack API endpoint string from a log line.
        
        Returns:
            The captured endpoint string if present, `None` otherwise.
        """
        pattern = r'API request to Slack endpoint: ([\w\.]+)'
        match = re.search(pattern, log_line)
        if match:
            return match.group(1)
        return None
    
    @staticmethod
    def extract_message_count(log_line: str) -> Optional[int]:
        """
        Extracts the number of messages retrieved from a log line.
        
        Parameters:
            log_line (str): Log entry text potentially containing a "Retrieved <N> messages" phrase.
        
        Returns:
            int | None: The number of messages if the pattern is found, otherwise None.
        """
        pattern = r'Retrieved (\d+) messages'
        match = re.search(pattern, log_line)
        if match:
            return int(match.group(1))
        return None
