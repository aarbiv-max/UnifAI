from typing import List, Dict, Optional, Any, cast
import hashlib
from datetime import datetime
from config.constants import PipelineStatus
from data_sources.docs.doc_connector import DocumentConnector, DuplicateDocumentError
from data_sources.docs.document_processor import DocumentProcessor
from data_sources.docs.pdf_chunker_strategy import PDFChunkerStrategy
from shared.source_types import DocumentMetadata
from config.constants import DataSource
from pipeline.pipeline import Pipeline
from utils.embedding.embedding_generator import EmbeddingGenerator
from utils.monitor.pipeline_monitor import PipelineMonitor
from utils.storage.vector_storage import VectorStorage
from threading import Thread
from providers.docs import handle_document_duplicate

class DocumentPipeline(Pipeline):
    SOURCE_TYPE = DataSource.DOCUMENT.upper_name
    def __init__(
        self,
        collector: DocumentConnector,
        processor: DocumentProcessor,
        chunker: PDFChunkerStrategy,
        embedder: EmbeddingGenerator,
        storage: VectorStorage,
        monitor: PipelineMonitor,
        metadata: DocumentMetadata
    ):
        self.collector = collector
        self.doc_processor = processor
        self.doc_chunker = chunker
        self.embedder = embedder
        self._cached_collected = None
        
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
        md = cast(DocumentMetadata, self.metadata)
        return md.doc_id

    def get_source_name(self) -> str:
        md = cast(DocumentMetadata, self.metadata)
        return md.doc_name or f"document_{md.doc_id}"

    def summary(self) -> Dict:
        if self._cached_collected:
            md = self._cached_collected.get("metadata", {})
            return {
                "page_count": md.get("page_count", 0),
                "full_text": self._cached_collected.get("text", ""),
                "file_size": md.get("file_size", 0),
                "content_md5": md.get("content_md5", ""),
            }
        else:
            return {
                "page_count": 0,
                "full_text": "",
                "file_size": 0,
                "content_md5": "",
            }

    def collect_data(self) -> Dict:
        try:
            md = cast(DocumentMetadata, self.metadata)
            self._cached_collected = self.collector.process_document(
                document_path=str(md.doc_path or ""),
                upload_by=str(md.upload_by or "default")
            )
        except DuplicateDocumentError as dup:
            try:
                handle_document_duplicate(
                    original_doc=getattr(dup, "original_doc", {}) or {},
                    duplicate_pipeline_id=self.get_pipeline_id(),
                    duplicate_source_name=self.get_source_name(),
                    uploader=str(cast(DocumentMetadata, self.metadata).upload_by or "default"),
                )
            except Exception:
                pass
            return {}
        
        return self._cached_collected or {}


    def process_data(self, data: Dict) -> Dict:
        return self.doc_processor.process(
            data,
            clean_markdown=False,
            clean_text=False,
            remove_references=False,
            preserve_original=True
        )

    def chunk_and_embed(self, processed: Dict) -> List[Dict]:
        embedding_ready_doc = self.doc_processor.prepare_for_single_doc_embedding(processed)
        chunks = self.doc_chunker.chunk_content([embedding_ready_doc])

        for idx, chunk in enumerate(chunks):
            mdict = chunk.setdefault("metadata", {})
            src_md = cast(DocumentMetadata, self.metadata)
            mdict.update({
                "source_id": src_md.doc_id,
                "source_type": DataSource.DOCUMENT.upper_name,
            })

        return self.embedder.generate_embeddings(chunks)

