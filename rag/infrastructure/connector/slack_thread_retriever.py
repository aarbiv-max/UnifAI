"""Slack thread retriever - infrastructure helper for SlackConnector."""
from typing import Dict, List, Any, Optional
from shared.logger import logger


class SlackThreadRetriever:
    """
    Helper class for retrieving threaded conversations from Slack.
    
    This class extends the functionality of SlackConnector to specifically
    handle threaded message retrieval.
    """
    
    def __init__(self, slack_connector):
        """
        Initialize SlackThreadRetriever with a SlackConnector instance.
        
        Stores the provided connector for making Slack API requests.
        """
        self._connector = slack_connector
    
    def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
        thread_number: int,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve messages from a Slack thread within optional time bounds.
        
        Parameters:
            channel_id: ID of the channel containing the thread.
            thread_ts: Timestamp of the parent (root) message of the thread.
            thread_number: Sequential identifier used for logging/tracing.
            oldest: Optional inclusive lower time bound (Slack timestamp) for messages to fetch.
            latest: Optional inclusive upper time bound (Slack timestamp) for messages to fetch.
        
        Returns:
            messages: List of message objects from the thread; returns an empty list if the Slack API reports an error.
        """
        params = {
            'channel': channel_id,
            'ts': thread_ts,
            'limit': 1000  # Maximum allowed by Slack API
        }
        if oldest:
            params['oldest'] = oldest
        if latest:
            params['latest'] = latest
        
        response = self._connector._make_api_request("conversations.replies", params)
        
        if not response.get('ok'):
            logger.error(f"Failed to get thread replies: {response.get('error')}")
            return []
        
        # The first message is the parent message, which we might already have
        messages = response.get('messages', [])
        logger.info(f"Fetching conversation replies (thread {thread_number}) for channel {channel_id}")
        logger.info(f"Retrieved {len(messages)} messages from thread {thread_number}")
        
        return messages
