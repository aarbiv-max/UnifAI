from typing import List, Dict
import hashlib
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
            # Mark as skipped and remember why (store reason under data_sources)
            repo.update_pipeline_status(self, PipelineStatus.SKIPPED.value)
            repo.sources_collection.update_one(
                {"pipeline_id": self.get_pipeline_id()},
                {"$set": {
                    "type_data.content_md5": dup.content_md5,
                    "type_data.skip_reason": "Duplicate document content (MD5)",
                    "type_data.duplicate_of_pipeline_id": dup.existing_pipeline_id,
                    "type_data.duplicate_of_source_id": dup.existing_source_id,
                }},
                upsert=True
            )
            # Update existing original doc with latest uploader and last_uploaded timestamp
            uploader = self.metadata.upload_by or "default"
            try:
                from datetime import datetime
                repo.sources_collection.update_many(
                    {
                        "source_type": self.SOURCE_TYPE,
                        "type_data.content_md5": dup.content_md5,
                        "pipeline_id": {"$ne": self.get_pipeline_id()}
                    },
                    [
                        {
                            "$set": {
                                "last_uploaded": datetime.utcnow(),
                                "upload_by": {
                                    "$cond": [
                                        {"$isArray": "$upload_by"},
                                        {"$setUnion": ["$upload_by", [uploader]]},
                                        {
                                            "$cond": [
                                                {"$eq": ["$upload_by", uploader]},
                                                "$upload_by",
                                                ["$upload_by", uploader]
                                            ]
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                )
            except Exception:
                pass
            # Stop further stages by returning empty dict
            return {}
        # Duplicate detection: compute MD5 of full text and check in sources
        try:
            full_text = (self._cached_collected or {}).get("text", "")
            content_md5 = hashlib.md5(full_text.encode("utf-8")).hexdigest() if full_text else None
            self._cached_collected.setdefault("metadata", {})["content_md5"] = content_md5
        except Exception:
            content_md5 = None

        if content_md5:
            repo = PipelineRepository()
            # Look for existing document with same hash (exclude current pipeline)
            existing = repo.sources_collection.find_one({
                "source_type": self.SOURCE_TYPE,
                "type_data.content_md5": content_md5,
                "pipeline_id": {"$ne": self.get_pipeline_id()}
            })
            if existing:
                # Mark as skipped and remember why (store reason under data_sources)
                repo.update_pipeline_status(self, PipelineStatus.SKIPPED.value)
                # Persist duplicate metadata on the new (skipped) pipeline doc
                repo.sources_collection.update_one(
                    {"pipeline_id": self.get_pipeline_id()},
                    {"$set": {
                        "type_data.content_md5": content_md5,
                        "type_data.skip_reason": "Duplicate document content (MD5)",
                        "type_data.duplicate_of_pipeline_id": existing.get("pipeline_id"),
                        "type_data.duplicate_of_source_id": existing.get("source_id"),
                    }},
                    upsert=True
                )
                # Update existing original doc with latest uploader and last_uploaded timestamp
                uploader = self.metadata.upload_by or "default"
                try:
                    from datetime import datetime
                    # Update all existing docs with same MD5 (excluding current) so the preferred one bubbles to top
                    repo.sources_collection.update_many(
                        {
                            "source_type": self.SOURCE_TYPE,
                            "type_data.content_md5": content_md5,
                            "pipeline_id": {"$ne": self.get_pipeline_id()}
                        },
                        [
                            {
                                "$set": {
                                    "last_uploaded": datetime.utcnow(),
                                    "upload_by": {
                                        "$cond": [
                                            {"$isArray": "$upload_by"},
                                            {"$setUnion": ["$upload_by", [uploader]]},
                                            {
                                                "$cond": [
                                                    {"$eq": ["$upload_by", uploader]},
                                                    "$upload_by",
                                                    ["$upload_by", uploader]
                                                ]
                                            }
                                        ]
                                    }
                                }
                            }
                        ]
                    )
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

        # After confirming not duplicate, persist MD5 on source.type_data
        try:
            content_md5 = processed.get("metadata", {}).get("content_md5")
            if content_md5:
                repo.sources_collection.update_one(
                    {"pipeline_id": self.get_pipeline_id()},
                    {"$set": {"type_data.content_md5": content_md5}},
                    upsert=True
                )
        except Exception:
            pass

        return self.embedder.generate_embeddings(chunks)
