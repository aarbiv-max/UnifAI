import re
from typing import Dict, List, Any

from domain.processor.data_processor import DataProcessor
from shared.logger import logger

class SlackProcessor(DataProcessor):
    """
    Processor for Slack message data.
    
    Handles the transformation of raw Slack message data into a clean,
    normalized format suitable for embedding in a vector database.
    """
    
    def __init__(self):
        """Initialize the Slack processor."""
        super().__init__()
        
    def process(self, data: List[Dict[str, Any]], channel_name: str) -> List[Dict[str, Any]]:
        """
        Normalize raw Slack conversation messages into processed records suitable for embedding.
        
        Parameters:
            data (List[Dict[str, Any]]): Raw Slack messages (as returned by conversations.history).
            channel_name (str): Slack channel name to attach to each message's metadata.
        
        Returns:
            List[Dict[str, Any]]: Processed messages. Each item contains:
                - `time_stamp`: original message `ts`
                - `user`: original message `user`
                - `text`: cleaned message text
                - `metadata`: dict with `channel_name` and optional `thread_ts` when present
        """
        logger.info(f"Starting to process {len(data)} Slack messages from channel: {channel_name}")
        
        self._data = data
        self._processed_data = []
        
        for message in data:
            # Skip messages without required fields
            if not all(key in message for key in ["ts", "user", "text"]):
                logger.debug(f"Skipping message due to missing required fields: {message}")
                continue
                
            # Create processed message with required fields
            processed_message = {
                "time_stamp": message["ts"],
                "user": message["user"],
                "text": self.clean_content(message["text"]),
                "metadata": {
                    "channel_name": channel_name
                }
            }
            
            # Add thread_ts if exists (for threaded messages)
            if "thread_ts" in message:
                processed_message["metadata"]["thread_ts"] = message["thread_ts"]
                
            self._processed_data.append(processed_message)
            
        logger.info(f"Finished processing Slack messages. Processed {len(self._processed_data)} out of {len(data)} messages")
        return self._processed_data
    
    def clean_content(self, content: str) -> str:
        """
        Normalize Slack message text by converting mentions, removing Slack-specific formatting, and normalizing URLs.
        
        Parameters:
            content (str): Raw message text from the Slack API.
        
        Returns:
            str: Cleaned text with user mentions converted to @user_id, channel mentions converted to #channel_name, Slack formatting markers (code blocks, inline code, bold, italic, strikethrough) removed, and Slack-style URLs converted to readable form (e.g., `<https://...|text>` -> `text`, `<https://...>` -> `https://...`). The result is stripped of leading/trailing whitespace.
        """
        if not content:
            return ""
            
        # Pass content through formatting handlers
        cleaned_text = self._handle_user_mentions(content)
        cleaned_text = self._handle_channel_mentions(cleaned_text)
        cleaned_text = self._handle_special_formatting(cleaned_text)
        cleaned_text = self._handle_urls(cleaned_text)
        
        return cleaned_text.strip()
    
    def _handle_user_mentions(self, text: str) -> str:
        """
        Normalize Slack user mentions of the form <@USER_ID> into @USER_ID.
        
        Returns:
            str: Text with Slack user mention tokens replaced by `@USER_ID`.
        """
        # For now, we're keeping the user ID but normalizing the format
        # Future enhancement: Replace with actual user names via the Slack Users API
        return re.sub(r'<@([A-Z0-9]+)>', r'@\1', text)
    
    def _handle_channel_mentions(self, text: str) -> str:
        """
        Convert Slack channel mentions of the form <#CHANNEL_ID|channel_name> into #channel_name.
        
        Parameters:
            text (str): Input text that may contain Slack channel mention tokens.
        
        Returns:
            str: Text with Slack channel mentions replaced by `#channel_name`.
        """
        import re
        return re.sub(r'<#([A-Z0-9]+)\|([^>]+)>', r'#\2', text)
    
    def _handle_special_formatting(self, text: str) -> str:
        """
        Strip Slack-specific formatting tokens from the given text.
        
        Removes code block and inline code delimiters (```...``` and `...`), emphasis markers for bold (`*...*`), italic (`_..._`), and strikethrough (`~...~`), preserving the enclosed content.
        
        Parameters:
            text (str): Text that may contain Slack formatting.
        
        Returns:
            str: The text with Slack formatting markers removed.
        """
        import re
        
        # Handle code blocks
        text = re.sub(r'```(.*?)```', r'\1', text, flags=re.DOTALL)
        text = re.sub(r'`(.*?)`', r'\1', text)
        
        # Handle bold and italic
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'_(.*?)_', r'\1', text)
        
        # Handle strikethrough
        text = re.sub(r'~(.*?)~', r'\1', text)
        
        return text
    
    def _handle_urls(self, text: str) -> str:
        """
        Normalize Slack-formatted URLs into plain text.
        
        Converts Slack angle-bracket URL forms so that `<https://example.com|label>` becomes `label`
        and `<https://example.com>` becomes `https://example.com`.
        
        Parameters:
            text (str): Input text that may contain Slack-formatted URLs.
        
        Returns:
            str: Text with Slack URL markup replaced by link labels or raw URLs.
        """
        import re
        
        # Replace <URL|text> with text
        text = re.sub(r'<(https?://[^|]+)\|([^>]+)>', r'\2', text)
        
        # Replace <URL> with URL
        text = re.sub(r'<(https?://[^>]+)>', r'\1', text)
        
        return text
        
    def batch_process(self, data_batches: List[Dict[str, Any]], channel_name: str) -> List[Dict[str, Any]]:
        """
        Process multiple message batches in parallel and return a flattened list of processed messages.
        
        Parameters:
            data_batches (Iterable[List[Dict[str, Any]]]): An iterable of message batches; each batch is a list of raw message dictionaries expected by process().
            channel_name (str): Slack channel name to attach to each processed message's metadata.
        
        Returns:
            List[Dict[str, Any]]: Combined list of processed message dictionaries from all batches.
        """
        from concurrent.futures import ThreadPoolExecutor
        
        logger.info(f"Starting parallel batch processing of {len(data_batches)} batches")
        all_processed = []
        
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(
                lambda batch: self.process(batch, channel_name), 
                data_batches
            ))
            
        for result in results:
            all_processed.extend(result)

        logger.info(f"Completed batch processing. Total processed messages: {len(all_processed)}")            
        return all_processed
