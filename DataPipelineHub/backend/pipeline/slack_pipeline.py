# pipelines/slack_pipeline.py

from typing import List, Dict, Tuple
from data_sources.slack.slack_data_processor import SlackProcessor
from data_sources.slack.slack_connector import SlackConnector
from data_sources.slack.slack_chunker_strategy import SlackChunkerStrategy
from shared.source_types import SlackMetadata
from config.constants import DataSource
from pipeline.pipeline import Pipeline
from utils.embedding.embedding_generator import EmbeddingGenerator
from utils.monitor.pipeline_monitor import PipelineMonitor
from utils.storage.vector_storage import VectorStorage


class SlackPipeline(Pipeline):
    SOURCE_TYPE = DataSource.SLACK.upper_name
    def __init__(
        self,
        collector: SlackConnector,
        processor: SlackProcessor,
        chunker: SlackChunkerStrategy,
        embedder: EmbeddingGenerator,
        storage: VectorStorage,
        metadata: SlackMetadata,
        monitor: PipelineMonitor,
    ):
        self.collector = collector
        self.slack_processor = processor
        self.slack_chunker = chunker
        self.embedder = embedder
        self.metadata = metadata
        
        super().__init__(
            collector=collector,
            processor=processor,
            chunker=chunker,
            embedder=embedder,
            storage=storage,
            monitor=monitor,
            metadata=metadata
        )

    def get_source_id(self) -> str:
        return self.metadata.channel_id

    def get_source_name(self) -> str:
        return self.metadata.channel_name
        
    def summary(self) -> Dict:
        return {
            "is_private": self.metadata.is_private,
        }
        
    def collect_data(self) -> Tuple[List[Dict], List[List[Dict]]]:
        return self.collector.get_conversations_history(
            channel_id=self.metadata.channel_id
        )

    def process_data(
        self, data: Tuple[List[Dict], List[List[Dict]]]
    ) -> Tuple[List[Dict], List[List[Dict]]]:
        messages, threads = data
        main = self.slack_processor.process(
            messages, channel_name=self.metadata.channel_name
        )
        thrs = [
            self.slack_processor.process(t, channel_name=self.metadata.channel_name)
            for t in threads
        ]
        return main, thrs

    def chunk_and_embed(
        self, processed: Tuple[List[Dict], List[List[Dict]]]
    ) -> List[Dict]:
        main, threads = processed
        chunks = self.slack_chunker.chunk_content(main)
        for t in threads:
            chunks.extend(self.slack_chunker.chunk_content(t))

        for idx, c in enumerate(chunks):
            md = c.setdefault("metadata", {})
            md.update({
                "source_id": self.metadata.channel_id,
                "chunk_index": idx,
                "source_type": DataSource.SLACK.upper_name,
            })

        return self.embedder.generate_embeddings(chunks)
