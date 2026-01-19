"""Slack chunking strategy implementation."""
from typing import Dict, List, Any, Union
from domain.vector.chunker import ContentChunker
import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter
from shared.logger import logger
from datetime import datetime


class SlackChunkerStrategy(ContentChunker):
    """
    Chunking strategy specifically designed for Slack conversations.
    
    Implements a hybrid chunking approach that:
    1. Preserves threads as intact chunks when possible
    2. Groups non-threaded messages by time proximity (conversation bursts)
    3. Enforces token limits for all chunks
    4. Maintains source traceability and metadata
    """
    
    def __init__(
        self, 
        max_tokens_per_chunk: int = 500, 
        overlap_tokens: int = 50,
        time_window_seconds: int = 300  # 5 minutes in seconds
    ):
        """
        Configure the Slack chunker with token limits, overlap, and conversation grouping window.
        
        Parameters:
            max_tokens_per_chunk: Maximum token count allowed for a single chunk; chunks exceeding this will be split.
            overlap_tokens: Number of tokens to overlap between adjacent chunks to preserve context across splits.
            time_window_seconds: Maximum time difference in seconds between messages to consider them part of the same conversation burst.
        
        Notes:
            Initializes an OpenAI-compatible tokenizer using the `cl100k_base` encoding for token estimation.
        """
        super().__init__(max_tokens_per_chunk, overlap_tokens)
        self.time_window_seconds = time_window_seconds
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # OpenAI's tokenizer, compatible with many embedding models
    
    def chunk_content(self, content: Union[List[Dict[str, Any]], List[List[Dict[str, Any]]]], upload_by: str = "default") -> List[Dict[str, Any]]:
        """
        Chunk Slack messages and threads into text chunks annotated with metadata.
        
        Preserves thread integrity when possible, groups non-threaded messages by time proximity, and enforces token-size limits so each returned chunk is within the configured size.
        
        Parameters:
            content (Union[List[Dict[str, Any]], List[List[Dict[str, Any]]]]): Either a flat list of message objects or a list of threads where each thread is a list of message objects. Each message is expected to include timestamp, user, text, and channel information.
            upload_by (str): Identifier for who uploaded or requested the chunking (stored in chunk metadata).
        
        Returns:
            List[Dict[str, Any]]: A list of chunk objects. Each chunk contains the chunk text and metadata such as source_type, channel, time range, message_count, token_count, and any split/chunk indexing information.
        """
        self._chunks = []
        
        # Determine if we're dealing with threads or individual messages
        if content and isinstance(content[0], list):
            logger.info(f"Processing {len(content)} Slack threads for chunking")
            self._chunk_threads(content, upload_by)
        else:
            logger.info(f"Processing {len(content)} individual Slack messages for chunking")
            self._chunk_individual_messages(content, upload_by)
        
        logger.info(f"Chunking complete. Generated {len(self._chunks)} chunks from Slack content")
        return self._chunks
    
    def _chunk_threads(self, threads: List[List[Dict[str, Any]]], upload_by) -> None:
        """
        Convert Slack threads into chunk dictionaries and append them to the instance's internal chunk list.
        
        Each thread is formatted and estimated for token length; if it fits within the configured token limit a single chunk is appended, otherwise the thread is split and multiple chunk entries are appended. Chunk metadata includes source_type, channel_name, upload_by, thread_id, time_range, message_count, and either token_count (for whole-thread chunks) or is_split plus chunk-specific metadata (for split fragments).
        
        Parameters:
            threads (List[List[Dict[str, Any]]]): List of threads, where each thread is a list of message dicts. Each message is expected to include a "time_stamp" and a "metadata" dict containing at least "channel_name"; an optional "thread_ts" in metadata may be used as the thread identifier.
            upload_by (str): Identifier for who uploaded or initiated the chunking; added to each chunk's metadata.
        """
        for thread_index, thread in enumerate(threads):
            if not thread:
                continue
                
            # Sort messages by timestamp to ensure proper ordering
            thread = sorted(thread, key=lambda msg: float(msg["time_stamp"]))
            
            # Check if the entire thread can fit in a single chunk
            thread_text = self._format_thread_as_text(thread)
            token_count = self.estimate_token_count(thread_text)
            
            # Get common metadata from the thread
            channel_name = thread[0]["metadata"]["channel_name"]
            first_timestamp = thread[0]["time_stamp"]
            last_timestamp = thread[-1]["time_stamp"]
            
            if token_count <= self.max_tokens_per_chunk:
                # The entire thread fits within token limits
                self._chunks.append({
                    "text": thread_text,
                    "metadata": {
                        "source_type": "slack_thread",
                        "channel_name": channel_name,
                        "upload_by": upload_by,
                        "thread_id": thread[0].get("metadata", {}).get("thread_ts", first_timestamp),
                        "time_range": f"{first_timestamp}-{last_timestamp}",
                        "message_count": len(thread),
                        "token_count": token_count
                    }
                })
            else:
                # Thread exceeds token limits, split it using LangChain's text splitter
                logger.debug(f"Thread {thread_index} exceeds token limit. Splitting into smaller chunks.")
                self._split_large_content(thread_text, {
                    "source_type": "slack_thread",
                    "channel_name": channel_name,
                    "upload_by": upload_by,
                    "thread_id": thread[0].get("metadata", {}).get("thread_ts", first_timestamp),
                    "time_range": f"{first_timestamp}-{last_timestamp}",
                    "message_count": len(thread),
                    "is_split": True
                })
    
    def _chunk_individual_messages(self, messages: List[Dict[str, Any]], upload_by) -> None:
        """
        Group non-thread Slack messages into time-windowed conversation bursts and produce token-limited chunks appended to self._chunks.
        
        Each burst contains messages whose timestamps are within self.time_window_seconds of each other. For each burst the function formats the messages as text, estimates token usage, and either appends a single chunk with metadata or splits the text into multiple chunks when it exceeds self.max_tokens_per_chunk. Appended chunk metadata includes source_type, channel_name, upload_by, time_range, message_count, token_count, and when splitting, an is_split flag and per-fragment chunk_index/chunk_count.
        
        Parameters:
            messages (List[Dict[str, Any]]): List of Slack message objects (not threaded). Each message is expected to include at least "time_stamp" and "metadata" with "channel_name", plus fields used by the formatter (e.g., user and text).
            upload_by (str): Identifier for who/uploaded the content; recorded in chunk metadata.
        """
        if not messages:
            return
            
        # Sort messages by timestamp
        messages = sorted(messages, key=lambda msg: float(msg["time_stamp"]))
        
        # Group messages by time proximity (conversation bursts)
        conversation_groups = []
        current_group = [messages[0]]
        
        for i in range(1, len(messages)):
            current_msg = messages[i]
            prev_msg = messages[i-1]
            
            time_diff = float(current_msg["time_stamp"]) - float(prev_msg["time_stamp"])
            
            if time_diff <= self.time_window_seconds:
                # Messages are close enough in time, add to current group
                current_group.append(current_msg)
            else:
                # Time gap exceeds window, start a new conversation group
                conversation_groups.append(current_group)
                current_group = [current_msg]
        
        # Add the last group if it exists
        if current_group:
            conversation_groups.append(current_group)
        
        logger.info(f"Grouped {len(messages)} messages into {len(conversation_groups)} conversation bursts")
        
        # Process each conversation group
        for group_index, group in enumerate(conversation_groups):
            channel_name = group[0]["metadata"]["channel_name"]
            first_timestamp = group[0]["time_stamp"]
            last_timestamp = group[-1]["time_stamp"]
            
            # Format the conversation as text
            conversation_text = self._format_messages_as_text(group)
            token_count = self.estimate_token_count(conversation_text)
            
            if token_count <= self.max_tokens_per_chunk:
                # Conversation fits within token limits
                self._chunks.append({
                    "text": conversation_text,
                    "metadata": {
                        "source_type": "slack_conversation",
                        "channel_name": channel_name,
                        "upload_by": upload_by,
                        "time_range": f"{first_timestamp}-{last_timestamp}",
                        "message_count": len(group),
                        "token_count": token_count
                    }
                })
            else:
                # Conversation exceeds token limits, split it
                logger.debug(f"Conversation group {group_index} exceeds token limit. Splitting into smaller chunks.")
                self._split_large_content(conversation_text, {
                    "source_type": "slack_conversation",
                    "channel_name": channel_name,
                    "upload_by": upload_by,
                    "time_range": f"{first_timestamp}-{last_timestamp}",
                    "message_count": len(group),
                    "is_split": True
                })
    
    def _split_large_content(self, text: str, metadata: Dict[str, Any]) -> None:
        """
        Split a text that exceeds token limits into smaller chunks and append them to self._chunks with updated metadata.
        
        Each resulting chunk is sized to respect the instance's max_tokens_per_chunk and overlap_tokens settings. The provided metadata is copied into each chunk and augmented with `chunk_index`, `chunk_count`, and `token_count` to preserve provenance and ordering.
        
        Parameters:
            text (str): The text content to split into smaller chunks.
            metadata (Dict[str, Any]): Base metadata to associate with each generated chunk; this dict will be copied and extended per chunk.
        """
        # Calculate approximately how many characters per token for this content
        chars_per_token = len(text) / max(1, self.estimate_token_count(text))
        
        # Convert token limits to character estimates for the text splitter
        max_chunk_size = int(self.max_tokens_per_chunk * chars_per_token)
        chunk_overlap = int(self.overlap_tokens * chars_per_token)
        
        # Create a recursive text splitter that tries to break at natural boundaries
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=lambda text: self.estimate_token_count(text),
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Split the text
        chunk_texts = text_splitter.split_text(text)
        
        # Create chunks with metadata
        for i, chunk_text in enumerate(chunk_texts):
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["chunk_count"] = len(chunk_texts)
            chunk_metadata["token_count"] = self.estimate_token_count(chunk_text)
            
            self._chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata
            })
    
    def _format_thread_as_text(self, thread_messages: List[Dict[str, Any]]) -> str:
        """
        Format a Slack thread's messages into a human-readable multiline text block.
        
        Each message is rendered on its own line prefixed with a readable timestamp and user. The output begins with a header containing the channel name and thread identifier.
        
        Parameters:
            thread_messages (List[Dict[str, Any]]): Ordered list of message objects where each message contains:
                - "time_stamp" (str | numeric): Unix timestamp of the message.
                - "user" (str): Display name or identifier of the message author.
                - "text" (str): Message content.
                - "metadata" (dict): Must include "channel_name" (str). May include "thread_ts" (str) to identify the thread.
        
        Returns:
            str: Multiline string representing the thread, with a header and one timestamped "user: text" line per message.
        """
        lines = []
        
        # Add thread header
        channel = thread_messages[0]["metadata"]["channel_name"]
        thread_ts = thread_messages[0].get("metadata", {}).get("thread_ts", thread_messages[0]["time_stamp"])
        lines.append(f"Slack Thread in #{channel} - Thread ID: {thread_ts}")
        lines.append("=" * 50)
        
        # Format each message in the thread
        for msg in thread_messages:
            timestamp = float(msg["time_stamp"])
            time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            user = msg["user"]
            text = msg["text"]
            
            lines.append(f"[{time_str}] {user}: {text}")
        
        return "\n".join(lines)
    
    def _format_messages_as_text(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format a list of Slack messages into a readable multi-line conversation text block.
        
        Parameters:
            messages (List[Dict[str, Any]]): Ordered list of message objects where each message contains:
                - "time_stamp": epoch timestamp (string or number),
                - "user": display name or identifier,
                - "text": message content,
                - "metadata": dict containing "channel_name".
        
        Returns:
            str: A multi-line string with a header showing channel and time range, a separator line,
                 and each message on its own line formatted as "[HH:MM:SS] user: text".
        """
        lines = []
        
        # Add conversation header
        channel = messages[0]["metadata"]["channel_name"]
        start_time = datetime.fromtimestamp(float(messages[0]["time_stamp"])).strftime('%Y-%m-%d %H:%M:%S')
        end_time = datetime.fromtimestamp(float(messages[-1]["time_stamp"])).strftime('%Y-%m-%d %H:%M:%S')
        
        lines.append(f"Slack Conversation in #{channel} - {start_time} to {end_time}")
        lines.append("=" * 50)
        
        # Format each message
        for msg in messages:
            timestamp = float(msg["time_stamp"])
            time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
            user = msg["user"]
            text = msg["text"]
            
            lines.append(f"[{time_str}] {user}: {text}")
        
        return "\n".join(lines)
    
    def estimate_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in the given text using the configured tokenizer.
        
        Returns:
            token_count (int): Number of tokens for the provided text; returns 0 for empty input.
        """
        if not text:
            return 0
            
        tokens = self.tokenizer.encode(text)
        return len(tokens)