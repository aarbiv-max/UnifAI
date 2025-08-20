from typing import List, Dict, Optional
import hashlib
from datetime import datetime
from config.constants import PipelineStatus
from pipeline.pipeline_repository import PipelineRepository
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
        return self.metadata.doc_id

    def get_source_name(self) -> str:
        return self.metadata.doc_name or f"document_{self.metadata.doc_id}"

    def summary(self) -> Dict:
        if self._cached_collected:
            return {
                "page_count": self._cached_collected.get("metadata", {}).get("page_count", 0),
                "full_text": self._cached_collected.get("text", ""),
                "file_size": self._cached_collected.get("metadata", {}).get("file_size", 0),
            }
        else:
            return {
                "page_count": 0,
                "full_text": "",
                "file_size": 0,
            }

    def collect_data(self) -> Dict:
        repo = PipelineRepository()
        try:
            self._cached_collected = self.collector.process_document(
                document_path=self.metadata.doc_path,
                upload_by=self.metadata.upload_by
            )
        except DuplicateDocumentError as dup:
            original_doc = getattr(dup, "original_doc", None)
            self.handle_duplication(original_doc)
            return {}
        
        # Persist MD5 under type_data immediately after collection (if available)
        try:
            content_md5 = (self._cached_collected or {}).get("metadata", {}).get("content_md5")
            if content_md5:
                repo.register_data_source(self, {"content_md5": content_md5})
        except Exception:
            pass

        return self._cached_collected


    def process_data(self, data: Dict) -> Dict:
        return self.doc_processor.process(
            data,
            clean_markdown=False,
            clean_text=False,
            remove_references=False,
            preserve_original=True
        )

    def chunk_and_embed(self, processed: Dict) -> List[Dict]:
        # If this pipeline was marked SKIPPED during collection, exit early
        repo = PipelineRepository()
        current_status = repo.get_pipeline_field(self.get_pipeline_id(), "status", PipelineStatus.PENDING.value)
        if current_status == PipelineStatus.SKIPPED.value:
            return []

        embedding_ready_doc = self.doc_processor.prepare_for_single_doc_embedding(processed)
        chunks = self.doc_chunker.chunk_content([embedding_ready_doc])

        for idx, chunk in enumerate(chunks):
            md = chunk.setdefault("metadata", {})
            md.update({
                "source_id": self.metadata.doc_id,
                "source_type": DataSource.DOCUMENT.upper_name,
            })

        return self.embedder.generate_embeddings(chunks)

    def handle_duplication(self, original_doc: Optional[Dict]) -> None:
        """
        Handle duplicate detection by:
        - Marking pipeline as SKIPPED
        - Updating the original source's last_updated to its created_at and merging uploader
        - Removing the duplicate source and pipeline documents
        """
        try:
            repo = PipelineRepository()
            repo.update_pipeline_status(self, PipelineStatus.SKIPPED.value)

            dup_id = self.get_pipeline_id()
            dup = repo.sources_collection.find_one({
                    "pipeline_id": dup_id
                }, {"created_at": 1}) or {}
            
            dup_created_at = dup.get("created_at", datetime.now())
            uploader = dup.get("upload_by", "default")

            repo.sources_collection.update_one(
                {"pipeline_id": original_doc.get("pipeline_id", "")},
                [{"$set": {"last_updated": dup_created_at, "upload_by": {
                    "$cond": [
                        {"$isArray": "$upload_by"},
                        {"$setUnion": ["$upload_by", [uploader]]},
                        {"$cond": [
                            {"$eq": ["$upload_by", uploader]},
                            "$upload_by",
                            ["$upload_by", uploader]
                        ]}
                    ]
                }}}]
            )
            repo.sources_collection.delete_one({"pipeline_id": dup_id})
            repo.pipelines_collection.delete_one({"pipeline_id": dup_id})
        except Exception:
            pass

