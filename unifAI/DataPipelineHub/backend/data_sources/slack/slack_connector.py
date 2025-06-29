import requests
import time
from typing import Dict, List, Optional, Any, Tuple
from shared.logger import logger
from .slack_config_manager import SlackConfigManager
from utils.data_connector import DataConnector
from .slack_thread_retriever import SlackThreadRetriever
from .slack_thread_retriever_worker import ThreadRetrieverWorker

class SlackConnector(DataConnector):
    """
    Connector for retrieving data from Slack.
    
    Handles authentication, rate limiting, and pagination for Slack API calls.
    """
    
    def __init__(self, config_manager: SlackConfigManager, project_id: Optional[str] = None):
        """
        Initialize the Slack connector.
        
        Args:
            config_manager: Configuration manager for Slack
            project_id: Optional project ID to use, defaults to the default project
        """
        super().__init__(config_manager)
        self.base_url = "https://slack.com/api/"
        self._available_apis = [
            "users.profile.get",
            "conversations.history",
            "conversations.list",
            "conversations.replies",
            "files.info",
        ]
        
        # Set the project ID
        self._project_id = project_id or config_manager.get_default_project()
        if not self._project_id:
            raise ValueError("No project ID provided and no default project set")
        
        # Get tokens for the project
        try:
            tokens = config_manager.get_project_tokens(self._project_id)
            self._user_token = tokens.get('user_token')
            self._bot_token = tokens.get('bot_token')
            
            if not self._bot_token:
                raise ValueError(f"Bot token not configured for project {self._project_id}")
                
        except KeyError as e:
            raise ValueError(f"Project tokens not found: {str(e)}")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Slack API using configured tokens.
        
        Returns:
            True if authentication succeeds, False otherwise
        """
        try:
            # Test authentication by calling the auth.test endpoint
            response = self._make_api_request("auth.test")
            
            if response.get('ok'):
                logger.info(f"Successfully authenticated with Slack as {response.get('user')}")
                return True
            else:
                logger.error(f"Slack authentication failed: {response.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Slack authentication error: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test connection to Slack API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        return self.authenticate()
    
    def _make_api_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                          method: str = "GET", use_user_token: bool = False) -> Dict[str, Any]:
        """
        Make a request to the Slack API with rate limiting handling.
        
        Args:
            endpoint: The API endpoint (without base URL)
            params: Optional parameters to send with the request
            method: HTTP method to use (GET or POST)
            use_user_token: Whether to use the user token instead of the bot token
            
        Returns:
            The response from the API as a dictionary
            
        Raises:
            Exception: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        token = self._user_token if use_user_token else self._bot_token
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        # Track retry attempts
        max_retries = 3
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                logger.info(f"Making API request to Slack endpoint: {endpoint}")
                
                if method.upper() == "GET":
                    response = requests.get(url, headers=headers, params=params)
                else:  # POST
                    response = requests.post(url, headers=headers, json=params)
                
                response_data = response.json()
                
                # Check for rate limiting
                if not response_data.get('ok') and response_data.get('error') == 'ratelimited':
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited by Slack API. Retrying in {retry_after} seconds.")
                    time.sleep(retry_after)
                    retry_count += 1
                    continue
                
                if not response_data.get('ok'):
                    logger.error(f"Slack API error: {response_data.get('error')}")
                else:
                    logger.info(f"Slack API request to {endpoint} successful")
                    
                return response_data
                
            except Exception as e:
                logger.error(f"Error making request to Slack API {endpoint}: {str(e)}")
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    retry_count += 1
                else:
                    raise
        
        # This should not be reached under normal circumstances
        raise Exception("Maximum retries exceeded when calling Slack API")
    
    def get_available_slack_channels(self, types: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get available Slack channels for the authenticated user/bot.
        
        Args:
            types: Optional channel types to filter by (e.g., 'public_channel,private_channel')
            
        Returns:
            List of dictionaries containing channel_id and channel_name
        """
        params = {}
        if types:
            params['types'] = types
        
        response = self._make_api_request("conversations.list", params)
        
        if not response.get('ok'):
            logger.error(f"Failed to get channels: {response.get('error')}")
            return []
        channels = []
        for channel in response.get('channels', []):
            channels.append({
                'channel_id': channel.get('id'),
                'channel_name': channel.get('name'),
                'is_private': channel.get('is_private', False),
            })
        
        logger.info(f"Retrieved {len(channels)} Slack channels")
        return channels
    
    def get_conversations_history(self, channel_id: str, limit: int = 1000, 
                               cursor: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[List[Dict[str, Any]]]]:
        """
        Get conversation history for a Slack channel with pagination handling and concurrently fetches thread replies.
        
        Args:
            channel_id: The ID of the channel to fetch history for
            limit: Maximum number of messages to return per page
            cursor: Pagination cursor from a previous request
        
        Returns:
            List of message objects from the conversation history
        """
        all_messages = []
        current_cursor = cursor
        has_more = True
        page = 1

        thread_retriever = SlackThreadRetriever(self)
        thread_worker = ThreadRetrieverWorker(thread_retriever)
        
        while has_more:
            params = {
                'channel': channel_id,
                'limit': limit
            }
            
            if current_cursor:
                params['cursor'] = current_cursor
            
            logger.info(f"Fetching conversation history (page {page}) for channel {channel_id}")
            response = self._make_api_request("conversations.history", params)
            
            if not response.get('ok'):
                logger.error(f"Failed to get conversation history: {response.get('error')}")
                break
                
            messages = response.get('messages', [])
            all_messages.extend(messages)
            logger.info(f"Retrieved {len(messages)} messages from channel {channel_id}")

            # Slack's conversations.history API only includes top-level messages in a channel, thread_replies aren't included in the response
            for msg in messages:
                # If the message is the parent of a thread, submit it to the thread worker queue
                if msg.get("thread_ts") == msg.get("ts"):
                    thread_worker.submit(channel_id, msg["ts"])
            
            # Check if there are more messages to fetch
            response_metadata = response.get('response_metadata', {})
            current_cursor = response_metadata.get('next_cursor')
            has_more = bool(current_cursor and response.get('has_more', False))
            page += 1
        
        logger.info(f"Retrieved a total of {len(all_messages)} messages from channel {channel_id}")
        
        # TODO: Consider whether to return directly 'thread_worker' under 'return' (in order to not block this entire function by calling thread_worker.gather_results()) 
        thread_messages = thread_worker.gather_results()
        logger.info(f"Retrieved a total of {len(thread_messages)} threads from channel {channel_id}")

        return all_messages, thread_messages