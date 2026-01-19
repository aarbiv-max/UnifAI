"""Slack Pipeline Handler - Source-specific pipeline operations for Slack."""
from typing import List, Dict, Any, Tuple

from domain.pipeline.port import SourcePipelinePort, PipelineContext
from domain.vector.embedder import EmbeddingGenerator
from domain.vector.model import VectorChunk
from domain.processor.slack_processor import SlackProcessor
from infrastructure.connector.slack_connector import SlackConnector
from infrastructure.chunking.slack_chunker import SlackChunkerStrategy
from shared.logger import logger

from global_utils.helpers.helpers import get_time_range_bounds_from_type_data


class SlackPipelineHandler(SourcePipelinePort):
    """
    Handler for Slack pipeline operations.
    
    Coordinates Slack-specific data flow through collection,
    processing, and embedding stages.
    
    This handler:
    - Collects messages and threads from Slack channels
    - Processes messages (normalizes text, handles mentions)
    - Chunks conversations and generates embeddings
    """
    
    def __init__(
        self,
        connector: SlackConnector,
        processor: SlackProcessor,
        chunker: SlackChunkerStrategy,
        embedder: EmbeddingGenerator,
    ):
        """
        Initialize the Slack pipeline handler.
        
        Args:
            connector: Slack connector for API communication
            processor: Slack processor for message transformation
            chunker: Slack chunker for conversation splitting
            embedder: Embedding generator for vector creation
        """
        self._connector = connector
        self._processor = processor
        self._chunker = chunker
        self._embedder = embedder
    
    @property
    def source_type(self) -> str:
        """
        Identify the pipeline source as Slack.
        
        Returns:
            str: The literal "SLACK" identifying the source type.
        """
        return "SLACK"
    
    def collect(self, context: PipelineContext) -> Tuple[List[Dict], List[List[Dict]]]:
        """
        Collect Slack messages and their threads for the pipeline context, optionally limited to a time range specified in context.metadata.
        
        Parameters:
            context (PipelineContext): Pipeline context containing source_id, source_name, and metadata; if metadata["type_data"] provides time bounds, they will be honored.
        
        Returns:
            Tuple[List[Dict], List[List[Dict]]]: A tuple where the first element is the list of main channel messages and the second is a list of thread message lists.
        """
        type_data = context.metadata.get("type_data")
        oldest, latest = get_time_range_bounds_from_type_data(type_data, output="slack_ts")
        
        if oldest or latest:
            logger.info(
                f"Fetching messages for channel {context.source_name} "
                f"in range oldest={oldest}, latest={latest}"
            )
            return self._connector.get_conversations_history(
                channel_id=context.source_id,
                oldest=oldest,
                latest=latest,
            )
        
        logger.info(
            f"Fetching all messages for channel {context.source_name} "
            "(no time range specified)"
        )
        return self._connector.get_conversations_history(
            channel_id=context.source_id,
        )
    
    def process(
        self, 
        context: PipelineContext, 
        raw_data: Tuple[List[Dict], List[List[Dict]]]
    ) -> Tuple[List[Dict], List[List[Dict]]]:
        """
        Normalize raw Slack messages and their threads for downstream processing.
        
        Parameters:
            context (PipelineContext): Pipeline context containing source and channel metadata used when processing messages.
            raw_data (Tuple[List[Dict], List[List[Dict]]]): Tuple of (main_messages, thread_messages) as returned by collect.
        
        Returns:
            Tuple[List[Dict], List[List[Dict]]]: A tuple (processed_main, processed_threads) where processed_main is the list of processed channel messages and processed_threads is a list of processed thread message lists.
        """
        messages, threads = raw_data
        
        processed_main = self._processor.process(
            messages, 
            channel_name=context.source_name
        )
        
        processed_threads = [
            self._processor.process(thread, channel_name=context.source_name)
            for thread in threads
        ]
        
        return processed_main, processed_threads
    
    def chunk_and_embed(
        self, 
        context: PipelineContext, 
        processed: Tuple[List[Dict], List[List[Dict]]]
    ) -> List[VectorChunk]:
        """
        Create chunks from processed Slack messages, attach Slack-specific metadata to each chunk, and return those chunks converted into VectorChunk objects with generated embeddings.
        
        Processes the provided processed data (main messages and per-thread messages), uses the configured chunker to produce text chunks (respecting an "upload_by" value in context.metadata, defaulting to "default"), enriches each chunk's metadata with "source_id", "source_type", and "chunk_index", generates embeddings for all chunks via the embedder, and maps the embedder's output into domain VectorChunk objects.
        
        Parameters:
            context: PipelineContext containing source identification and metadata (used for "upload_by" and source metadata).
            processed: Tuple of (processed_main, processed_threads) where `processed_main` is a list of processed message dicts and `processed_threads` is a list of lists of processed message dicts (one list per thread).
        
        Returns:
            List of VectorChunk: each contains the chunk text, its embedding (as a plain list), and the chunk's metadata.
        """
        main, threads = processed
        upload_by = context.metadata.get("upload_by", "default")
        
        # Chunk main messages
        chunks = self._chunker.chunk_content(main, upload_by=upload_by)
        
        # Chunk thread messages
        for thread in threads:
            chunks.extend(self._chunker.chunk_content(thread, upload_by=upload_by))
        
        # Enrich with source metadata
        for idx, chunk in enumerate(chunks):
            chunk.setdefault("metadata", {}).update({
                "source_id": context.source_id,
                "source_type": self.source_type,
                "chunk_index": idx,
            })
        
        # Generate embeddings and convert to domain objects
        enriched_dicts = self._embedder.generate_embeddings(chunks)
        
        return [
            VectorChunk(
                text=d["text"],
                embedding=d["embedding"].tolist() if hasattr(d["embedding"], 'tolist') else d["embedding"],
                metadata=d.get("metadata", {})
            )
            for d in enriched_dicts
        ]
    
    def get_summary(self, context: PipelineContext, collected: Any) -> Dict:
        """
        Return a Slack-specific execution summary containing privacy metadata.
        
        Returns:
            dict: Summary with key "is_private" set to the value of context.metadata.get("is_private").
        """
        return {
            "is_private": context.metadata.get("is_private"),
        }
