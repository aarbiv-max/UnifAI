"""
End-to-End Test: FULL LOCAL Orchestration Pipeline

This test simulates the complete pipeline orchestration as it runs in production,
but using LOCAL components (no external services):

1. DocumentPipelineHandler.collect() - Document processing via local docling
2. DocumentPipelineHandler.process() - Text processing
3. DocumentPipelineHandler.chunk_and_embed() - Chunking + local embedding
4. Storage simulation (without actual Qdrant)

This tests the SAME flow that Celery workers execute, but synchronously.

Requires TEST_DOCUMENT_PATH environment variable.

Run:
    TEST_DOCUMENT_PATH=/path/to/test.pdf pytest tests/e2e/test_e2e_orchestration_local.py -v -s
"""

import os
import time
import uuid
import pytest
import numpy as np
from typing import Dict, Any, List
from dataclasses import dataclass


# Skip all tests if test document not configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DOCUMENT_PATH") or not os.path.exists(os.environ.get("TEST_DOCUMENT_PATH", "")),
    reason="TEST_DOCUMENT_PATH not set or file does not exist"
)


class TestE2EOrchestrationLocal:
    """End-to-end orchestration test using local components."""

    @pytest.fixture(autouse=True)
    def setup(self, test_document_path, embedding_model_name, test_report):
        """Initialize all components for orchestration test."""
        from infrastructure.connector.document_connector import DocumentConnector
        from infrastructure.embedding.sentence_transformer_embedder import SentenceTransformerEmbedding
        from infrastructure.config.doc_config_manager import DocConfigManager
        from infrastructure.chunking.pdf_chunker import PDFChunkerStrategy
        from domain.processor.document_processor import DocumentProcessor
        from application.pipeline.document_handler import DocumentPipelineHandler
        from domain.pipeline.port import PipelineContext
        
        # Initialize components (local mode)
        config_manager = DocConfigManager()
        
        self.doc_connector = DocumentConnector(config_manager=config_manager)
        self.embedder = SentenceTransformerEmbedding(
            model_name=embedding_model_name,
            batch_size=32,
            device="cpu",
        )
        self.processor = DocumentProcessor()
        self.chunker = PDFChunkerStrategy(
            max_tokens_per_chunk=500,
            overlap_tokens=50,
        )
        
        # Create pipeline handler
        self.handler = DocumentPipelineHandler(
            connector=self.doc_connector,
            processor=self.processor,
            chunker=self.chunker,
            embedder=self.embedder,
        )
        
        # Create pipeline context
        self.pipeline_id = str(uuid.uuid4())
        self.source_id = f"doc_{uuid.uuid4().hex[:8]}"
        self.context = PipelineContext(
            pipeline_id=self.pipeline_id,
            source_type="DOCUMENT",
            source_id=self.source_id,
            source_name=os.path.basename(test_document_path),
            metadata={
                "doc_path": test_document_path,
                "doc_id": self.source_id,
                "doc_name": os.path.basename(test_document_path),
                "upload_by": "e2e_test_user",
            },
        )
        
        self.test_document_path = test_document_path
        self.create_report = test_report
        self.PipelineContext = PipelineContext

    def test_orchestration_initialization(self):
        """Test that all orchestration components initialize correctly."""
        report = self.create_report("Orchestration Initialization", "local")
        
        report.add_metric("doc_connector_is_remote", self.doc_connector.is_remote)
        report.add_metric("embedder_is_remote", self.embedder.is_remote)
        report.add_metric("embedding_dim", self.embedder.embedding_dim)
        report.add_detail("handler_type", type(self.handler).__name__)
        report.add_detail("handler_source_type", self.handler.source_type)
        report.add_detail("pipeline_id", self.pipeline_id)
        report.add_detail("source_id", self.source_id)
        report.add_detail("context_source_name", self.context.source_name)
        
        report.print_report()
        
        assert self.handler.source_type == "DOCUMENT"
        assert self.doc_connector.is_remote is False
        assert self.embedder.is_remote is False

    def test_step1_collect(self):
        """Test Step 1: Document Collection."""
        report = self.create_report("Step 1: Collect", "local")
        
        start_time = time.time()
        collected = self.handler.collect(self.context)
        elapsed = time.time() - start_time
        
        report.add_metric("collect_time_seconds", elapsed)
        report.add_metric("text_length_chars", len(collected.get("text", "")))
        report.add_metric("text_length_words", len(collected.get("text", "").split()))
        report.add_metric("markdown_length_chars", len(collected.get("markdown", "")))
        report.add_detail("collected_keys", list(collected.keys()))
        report.add_detail("filename", collected.get("filename"))
        report.add_detail("path", collected.get("path"))
        
        if "metadata" in collected:
            report.add_detail("metadata_keys", list(collected["metadata"].keys()))
        
        report.add_detail("text_preview", collected.get("text", "")[:300] + "...")
        
        report.print_report()
        
        assert collected is not None
        assert len(collected.get("text", "")) > 0

    def test_step2_process(self):
        """Test Step 2: Document Processing."""
        report = self.create_report("Step 2: Process", "local")
        
        # First collect
        collected = self.handler.collect(self.context)
        
        # Then process
        start_time = time.time()
        processed = self.handler.process(self.context, collected)
        elapsed = time.time() - start_time
        
        report.add_metric("process_time_seconds", elapsed)
        report.add_metric("processed_text_length", len(processed.get("text", "")))
        report.add_detail("processed_keys", list(processed.keys()))
        
        # Check if text changed during processing
        original_len = len(collected.get("text", ""))
        processed_len = len(processed.get("text", ""))
        report.add_metric("text_length_change", processed_len - original_len)
        report.add_metric("text_preserved", processed_len >= original_len * 0.9)
        
        report.print_report()
        
        assert processed is not None

    def test_step3_chunk_and_embed(self):
        """Test Step 3: Chunking and Embedding."""
        report = self.create_report("Step 3: Chunk & Embed", "local")
        
        # Collect and process first
        collected = self.handler.collect(self.context)
        processed = self.handler.process(self.context, collected)
        
        # Chunk and embed
        start_time = time.time()
        vector_chunks = self.handler.chunk_and_embed(self.context, processed)
        elapsed = time.time() - start_time
        
        report.add_metric("chunk_embed_time_seconds", elapsed)
        report.add_metric("vector_chunk_count", len(vector_chunks))
        
        if vector_chunks:
            # Analyze chunks
            chunk_lengths = [len(vc.text) for vc in vector_chunks]
            embedding_dims = [len(vc.embedding) for vc in vector_chunks]
            
            report.add_metric("avg_chunk_length", np.mean(chunk_lengths))
            report.add_metric("min_chunk_length", np.min(chunk_lengths))
            report.add_metric("max_chunk_length", np.max(chunk_lengths))
            report.add_metric("embedding_dimension", embedding_dims[0])
            report.add_metric("chunks_per_second", len(vector_chunks) / elapsed if elapsed > 0 else 0)
            
            # Check metadata
            first_chunk = vector_chunks[0]
            report.add_detail("first_chunk_text", first_chunk.text[:100] + "...")
            report.add_detail("first_chunk_metadata", first_chunk.metadata)
            report.add_detail("embedding_sample", first_chunk.embedding[:5])
        
        report.print_report()
        
        assert len(vector_chunks) > 0
        for vc in vector_chunks:
            assert vc.text
            assert len(vc.embedding) == self.embedder.embedding_dim
            assert vc.metadata.get("source_id") == self.source_id
            assert vc.metadata.get("source_type") == "DOCUMENT"

    def test_full_pipeline_orchestration(self):
        """Test complete pipeline orchestration (all steps)."""
        report = self.create_report("Full Pipeline Orchestration", "local")
        
        total_start = time.time()
        step_times = {}
        
        # Step 1: Collect
        step_start = time.time()
        collected = self.handler.collect(self.context)
        step_times["collect"] = time.time() - step_start
        
        # Step 2: Process
        step_start = time.time()
        processed = self.handler.process(self.context, collected)
        step_times["process"] = time.time() - step_start
        
        # Step 3: Chunk & Embed
        step_start = time.time()
        vector_chunks = self.handler.chunk_and_embed(self.context, processed)
        step_times["chunk_embed"] = time.time() - step_start
        
        # Step 4: Get Summary
        step_start = time.time()
        summary = self.handler.get_summary(self.context, collected)
        step_times["summary"] = time.time() - step_start
        
        # Step 5: Cleanup (simulate - don't actually delete test file)
        step_times["cleanup"] = 0  # Skipped for test
        
        total_time = time.time() - total_start
        
        # Report metrics
        report.add_metric("total_time_seconds", total_time)
        for step, duration in step_times.items():
            report.add_metric(f"step_{step}_seconds", duration)
            report.add_metric(f"step_{step}_percent", (duration / total_time) * 100 if total_time > 0 else 0)
        
        report.add_metric("vector_chunks_produced", len(vector_chunks))
        report.add_metric("text_chars_processed", len(collected.get("text", "")))
        
        # Summary info
        report.add_detail("summary", summary)
        report.add_detail("pipeline_id", self.pipeline_id)
        report.add_detail("source_id", self.source_id)
        
        # Chunk analysis
        if vector_chunks:
            total_chunk_chars = sum(len(vc.text) for vc in vector_chunks)
            report.add_metric("total_chunk_chars", total_chunk_chars)
            report.add_metric("avg_embedding_values", np.mean([np.mean(vc.embedding) for vc in vector_chunks]))
        
        report.print_report()
        
        # Assertions
        assert len(vector_chunks) > 0
        assert summary is not None
        assert total_time > 0

    def test_pipeline_with_simulated_storage(self):
        """Test pipeline with simulated vector storage."""
        report = self.create_report("Pipeline + Simulated Storage", "local")
        
        # Run pipeline
        collected = self.handler.collect(self.context)
        processed = self.handler.process(self.context, collected)
        vector_chunks = self.handler.chunk_and_embed(self.context, processed)
        
        # Simulate storage
        stored_vectors = []
        for vc in vector_chunks:
            stored_vectors.append({
                "id": str(uuid.uuid4()),
                "text": vc.text,
                "embedding": vc.embedding,
                "metadata": vc.metadata,
            })
        
        report.add_metric("vectors_to_store", len(vector_chunks))
        report.add_metric("vectors_stored", len(stored_vectors))
        report.add_metric("storage_success", len(stored_vectors) == len(vector_chunks))
        
        # Simulate vector search
        query = "main topic of the document"
        query_embedding = self.embedder.generate_query_embedding(query)
        
        def cosine_sim(a, b):
            a = np.array(a)
            b = np.array(b)
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        
        search_results = []
        for sv in stored_vectors:
            sim = cosine_sim(query_embedding, sv["embedding"])
            search_results.append({
                "id": sv["id"],
                "score": sim,
                "text_preview": sv["text"][:50] + "...",
            })
        
        search_results.sort(key=lambda x: x["score"], reverse=True)
        
        report.add_metric("search_top_score", search_results[0]["score"] if search_results else 0)
        report.add_detail("search_query", query)
        report.add_detail("top_3_results", search_results[:3])
        
        report.print_report()
        
        assert len(stored_vectors) == len(vector_chunks)

    def test_pipeline_context_building(self):
        """Test building PipelineContext from source_data (like Celery task does)."""
        report = self.create_report("Context Building", "local")
        
        # Simulate source_data as it comes from registration
        source_data = {
            "pipeline_id": str(uuid.uuid4()),
            "metadata": {
                "doc_id": "test_doc_123",
                "doc_name": "test_document.pdf",
                "doc_path": self.test_document_path,
                "upload_by": "test_user",
            },
            "type_data": {
                "chunk_size": 500,
                "overlap": 50,
            },
        }
        
        # Build context (same logic as Celery task)
        from infrastructure.celery.workers.pipeline_tasks import build_context
        
        context = build_context("DOCUMENT", source_data)
        
        report.add_detail("source_data", source_data)
        report.add_detail("built_context_pipeline_id", context.pipeline_id)
        report.add_detail("built_context_source_type", context.source_type)
        report.add_detail("built_context_source_id", context.source_id)
        report.add_detail("built_context_source_name", context.source_name)
        report.add_detail("built_context_metadata_keys", list(context.metadata.keys()))
        
        report.add_metric("context_built_successfully", True)
        
        report.print_report()
        
        assert context.pipeline_id == source_data["pipeline_id"]
        assert context.source_type == "DOCUMENT"
        assert context.source_id == "test_doc_123"

    def test_error_handling_invalid_path(self):
        """Test error handling when document path is invalid."""
        report = self.create_report("Error Handling - Invalid Path", "local")
        
        from infrastructure.connector.document_connector import DoclingProcessingError
        
        # Create context with invalid path
        invalid_context = self.PipelineContext(
            pipeline_id=str(uuid.uuid4()),
            source_type="DOCUMENT",
            source_id="invalid_doc",
            source_name="nonexistent.pdf",
            metadata={
                "doc_path": "/nonexistent/path/document.pdf",
                "upload_by": "test_user",
            },
        )
        
        error_raised = False
        error_message = None
        
        try:
            self.handler.collect(invalid_context)
        except DoclingProcessingError as e:
            error_raised = True
            error_message = str(e)
        except Exception as e:
            error_raised = True
            error_message = f"Unexpected error: {str(e)}"
        
        report.add_metric("error_raised", error_raised)
        report.add_detail("error_message", error_message)
        report.add_detail("invalid_path", "/nonexistent/path/document.pdf")
        
        report.print_report()
        
        assert error_raised, "Should raise error for invalid path"

    def test_handler_summary(self):
        """Test handler summary generation."""
        report = self.create_report("Handler Summary", "local")
        
        # Run collect to populate cached data
        collected = self.handler.collect(self.context)
        
        # Get summary
        summary = self.handler.get_summary(self.context, collected)
        
        report.add_detail("summary_keys", list(summary.keys()))
        
        for key, value in summary.items():
            if isinstance(value, (int, float)):
                report.add_metric(f"summary_{key}", value)
            elif isinstance(value, str) and len(value) > 100:
                report.add_detail(f"summary_{key}", f"{value[:100]}... ({len(value)} chars)")
            else:
                report.add_detail(f"summary_{key}", value)
        
        report.print_report()
        
        assert summary is not None
        assert "page_count" in summary or "full_text" in summary
