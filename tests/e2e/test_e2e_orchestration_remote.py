"""
End-to-End Test: FULL REMOTE Orchestration Pipeline

This test simulates the complete pipeline orchestration using REMOTE services:

1. DocumentPipelineHandler.collect() - Document processing via remote docling service
2. DocumentPipelineHandler.process() - Text processing
3. DocumentPipelineHandler.chunk_and_embed() - Chunking + remote embedding service
4. Storage simulation (without actual Qdrant)

This tests the SAME flow that Celery workers execute in production, but synchronously.

Requires:
    - DOCLING_SERVICE_URL environment variable
    - EMBEDDING_SERVICE_URL environment variable
    - TEST_DOCUMENT_PATH environment variable

Run:
    DOCLING_SERVICE_URL=http://docling-service:5001 \
    EMBEDDING_SERVICE_URL=http://embedding-service:5002 \
    TEST_DOCUMENT_PATH=/path/to/test.pdf \
    pytest tests/e2e/test_e2e_orchestration_remote.py -v -s
"""

import os
import time
import uuid
import pytest
import numpy as np
from typing import Dict, Any, List


# Skip all tests if required env vars not configured
pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("DOCLING_SERVICE_URL"),
        reason="DOCLING_SERVICE_URL not set"
    ),
    pytest.mark.skipif(
        not os.environ.get("EMBEDDING_SERVICE_URL"),
        reason="EMBEDDING_SERVICE_URL not set"
    ),
    pytest.mark.skipif(
        not os.environ.get("TEST_DOCUMENT_PATH") or not os.path.exists(os.environ.get("TEST_DOCUMENT_PATH", "")),
        reason="TEST_DOCUMENT_PATH not set or file does not exist"
    ),
]


class TestE2EOrchestrationRemote:
    """End-to-end orchestration test using remote services."""

    @pytest.fixture(autouse=True)
    def setup(
        self, 
        test_document_path, 
        docling_service_url,
        docling_service_timeout,
        embedding_service_url,
        embedding_service_timeout,
        embedding_model_name,
        test_report
    ):
        """Initialize all components for orchestration test with remote services."""
        from infrastructure.connector.document_connector import DocumentConnector
        from infrastructure.embedding.sentence_transformer_embedder import SentenceTransformerEmbedding
        from infrastructure.config.doc_config_manager import DocConfigManager
        from infrastructure.chunking.pdf_chunker import PDFChunkerStrategy
        from domain.processor.document_processor import DocumentProcessor
        from application.pipeline.document_handler import DocumentPipelineHandler
        from domain.pipeline.port import PipelineContext
        from global_utils.clients import DoclingServiceClient, EmbeddingServiceClient
        
        # Initialize components (remote mode)
        config_manager = DocConfigManager()
        
        # Remote document connector
        docling_client = DoclingServiceClient(
            base_url=docling_service_url,
            timeout=docling_service_timeout,
        )
        self.doc_connector = DocumentConnector(
            config_manager=config_manager,
            service_client=docling_client,
        )
        
        # Remote embedder
        embedding_client = EmbeddingServiceClient(
            base_url=embedding_service_url,
            timeout=embedding_service_timeout,
            model_name=embedding_model_name,
        )
        self.embedder = SentenceTransformerEmbedding(
            service_client=embedding_client,
            batch_size=32,
            embedding_dim=384,
        )
        
        self.processor = DocumentProcessor()
        self.chunker = PDFChunkerStrategy(
            max_tokens_per_chunk=500,
            overlap_tokens=50,
        )
        
        # Create pipeline handler with remote components
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
        self.docling_service_url = docling_service_url
        self.embedding_service_url = embedding_service_url
        self.create_report = test_report
        self.PipelineContext = PipelineContext

    def _check_services(self) -> Dict[str, bool]:
        """Check if both services are available."""
        import requests
        
        docling_ok = False
        embedding_ok = False
        
        try:
            resp = requests.get(f"{self.docling_service_url}/health", timeout=10)
            docling_ok = resp.status_code == 200
        except:
            pass
        
        try:
            resp = requests.get(f"{self.embedding_service_url}/health", timeout=10)
            embedding_ok = resp.status_code == 200
        except:
            pass
        
        return {"docling": docling_ok, "embedding": embedding_ok}

    def test_orchestration_initialization(self):
        """Test that all orchestration components initialize correctly."""
        report = self.create_report("Orchestration Initialization", "remote")
        
        report.add_metric("doc_connector_is_remote", self.doc_connector.is_remote)
        report.add_metric("embedder_is_remote", self.embedder.is_remote)
        report.add_metric("embedding_dim", self.embedder.embedding_dim)
        report.add_detail("handler_type", type(self.handler).__name__)
        report.add_detail("handler_source_type", self.handler.source_type)
        report.add_detail("pipeline_id", self.pipeline_id)
        report.add_detail("source_id", self.source_id)
        report.add_detail("docling_service_url", self.docling_service_url)
        report.add_detail("embedding_service_url", self.embedding_service_url)
        
        report.print_report()
        
        assert self.handler.source_type == "DOCUMENT"
        assert self.doc_connector.is_remote is True
        assert self.embedder.is_remote is True

    def test_services_connectivity(self):
        """Test connectivity to both remote services."""
        report = self.create_report("Services Connectivity", "remote")
        
        services = self._check_services()
        
        report.add_metric("docling_service_available", services["docling"])
        report.add_metric("embedding_service_available", services["embedding"])
        report.add_detail("docling_url", self.docling_service_url)
        report.add_detail("embedding_url", self.embedding_service_url)
        
        report.print_report()
        
        if not services["docling"]:
            pytest.skip("Docling service not available")
        if not services["embedding"]:
            pytest.skip("Embedding service not available")

    def test_step1_collect(self):
        """Test Step 1: Document Collection via remote service."""
        report = self.create_report("Step 1: Collect", "remote")
        
        services = self._check_services()
        if not services["docling"]:
            pytest.skip("Docling service not available")
        
        start_time = time.time()
        collected = self.handler.collect(self.context)
        elapsed = time.time() - start_time
        
        report.add_metric("collect_time_seconds", elapsed)
        report.add_metric("text_length_chars", len(collected.get("text", "")))
        report.add_metric("text_length_words", len(collected.get("text", "").split()))
        report.add_metric("markdown_length_chars", len(collected.get("markdown", "")))
        report.add_detail("collected_keys", list(collected.keys()))
        report.add_detail("text_preview", collected.get("text", "")[:300] + "...")
        
        report.print_report()
        
        assert collected is not None
        assert len(collected.get("text", "")) > 0

    def test_step2_process(self):
        """Test Step 2: Document Processing."""
        report = self.create_report("Step 2: Process", "remote")
        
        services = self._check_services()
        if not services["docling"]:
            pytest.skip("Docling service not available")
        
        collected = self.handler.collect(self.context)
        
        start_time = time.time()
        processed = self.handler.process(self.context, collected)
        elapsed = time.time() - start_time
        
        report.add_metric("process_time_seconds", elapsed)
        report.add_metric("processed_text_length", len(processed.get("text", "")))
        report.add_detail("processed_keys", list(processed.keys()))
        
        report.print_report()
        
        assert processed is not None

    def test_step3_chunk_and_embed(self):
        """Test Step 3: Chunking and Embedding via remote service."""
        report = self.create_report("Step 3: Chunk & Embed", "remote")
        
        services = self._check_services()
        if not all(services.values()):
            pytest.skip(f"Services not available: {services}")
        
        collected = self.handler.collect(self.context)
        processed = self.handler.process(self.context, collected)
        
        start_time = time.time()
        vector_chunks = self.handler.chunk_and_embed(self.context, processed)
        elapsed = time.time() - start_time
        
        report.add_metric("chunk_embed_time_seconds", elapsed)
        report.add_metric("vector_chunk_count", len(vector_chunks))
        
        if vector_chunks:
            chunk_lengths = [len(vc.text) for vc in vector_chunks]
            embedding_dims = [len(vc.embedding) for vc in vector_chunks]
            
            report.add_metric("avg_chunk_length", np.mean(chunk_lengths))
            report.add_metric("embedding_dimension", embedding_dims[0])
            report.add_metric("chunks_per_second", len(vector_chunks) / elapsed if elapsed > 0 else 0)
            
            first_chunk = vector_chunks[0]
            report.add_detail("first_chunk_text", first_chunk.text[:100] + "...")
            report.add_detail("first_chunk_metadata", first_chunk.metadata)
        
        report.print_report()
        
        assert len(vector_chunks) > 0

    def test_full_pipeline_orchestration(self):
        """Test complete pipeline orchestration with remote services."""
        report = self.create_report("Full Pipeline Orchestration", "remote")
        
        services = self._check_services()
        if not all(services.values()):
            pytest.skip(f"Services not available: {services}")
        
        total_start = time.time()
        step_times = {}
        network_times = {}
        
        # Step 1: Collect (network call to docling)
        step_start = time.time()
        collected = self.handler.collect(self.context)
        step_times["collect"] = time.time() - step_start
        network_times["docling"] = step_times["collect"]
        
        # Step 2: Process (local)
        step_start = time.time()
        processed = self.handler.process(self.context, collected)
        step_times["process"] = time.time() - step_start
        
        # Step 3: Chunk & Embed (network call to embedding)
        step_start = time.time()
        vector_chunks = self.handler.chunk_and_embed(self.context, processed)
        step_times["chunk_embed"] = time.time() - step_start
        network_times["embedding"] = step_times["chunk_embed"]
        
        # Step 4: Get Summary (local)
        step_start = time.time()
        summary = self.handler.get_summary(self.context, collected)
        step_times["summary"] = time.time() - step_start
        
        total_time = time.time() - total_start
        total_network_time = sum(network_times.values())
        
        # Report metrics
        report.add_metric("total_time_seconds", total_time)
        report.add_metric("total_network_time_seconds", total_network_time)
        report.add_metric("network_overhead_percent", (total_network_time / total_time) * 100)
        
        for step, duration in step_times.items():
            report.add_metric(f"step_{step}_seconds", duration)
            report.add_metric(f"step_{step}_percent", (duration / total_time) * 100)
        
        report.add_metric("vector_chunks_produced", len(vector_chunks))
        report.add_metric("text_chars_processed", len(collected.get("text", "")))
        
        # Latency breakdown
        report.add_detail("network_breakdown", network_times)
        report.add_detail("summary", summary)
        
        report.print_report()
        
        assert len(vector_chunks) > 0
        assert total_time > 0

    def test_pipeline_latency_analysis(self):
        """Detailed latency analysis for remote pipeline."""
        report = self.create_report("Latency Analysis", "remote")
        
        services = self._check_services()
        if not all(services.values()):
            pytest.skip(f"Services not available: {services}")
        
        num_runs = 3
        all_latencies = {
            "collect": [],
            "process": [],
            "chunk_embed": [],
            "total": [],
        }
        
        for i in range(num_runs):
            total_start = time.time()
            
            start = time.time()
            collected = self.handler.collect(self.context)
            all_latencies["collect"].append(time.time() - start)
            
            start = time.time()
            processed = self.handler.process(self.context, collected)
            all_latencies["process"].append(time.time() - start)
            
            start = time.time()
            self.handler.chunk_and_embed(self.context, processed)
            all_latencies["chunk_embed"].append(time.time() - start)
            
            all_latencies["total"].append(time.time() - total_start)
        
        # Statistics
        for key, values in all_latencies.items():
            report.add_metric(f"{key}_avg_seconds", np.mean(values))
            report.add_metric(f"{key}_min_seconds", np.min(values))
            report.add_metric(f"{key}_max_seconds", np.max(values))
            report.add_metric(f"{key}_std_seconds", np.std(values))
        
        # Percentage breakdown
        total_avg = np.mean(all_latencies["total"])
        report.add_metric("collect_percent", (np.mean(all_latencies["collect"]) / total_avg) * 100)
        report.add_metric("process_percent", (np.mean(all_latencies["process"]) / total_avg) * 100)
        report.add_metric("chunk_embed_percent", (np.mean(all_latencies["chunk_embed"]) / total_avg) * 100)
        
        report.add_detail("num_runs", num_runs)
        report.add_detail("all_latencies", all_latencies)
        
        report.print_report()

    def test_pipeline_with_simulated_storage(self):
        """Test pipeline with simulated vector storage."""
        report = self.create_report("Pipeline + Simulated Storage", "remote")
        
        services = self._check_services()
        if not all(services.values()):
            pytest.skip(f"Services not available: {services}")
        
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
        
        # Simulate search
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

    def test_remote_consistency(self):
        """Test that remote pipeline produces consistent results."""
        report = self.create_report("Remote Consistency", "remote")
        
        services = self._check_services()
        if not all(services.values()):
            pytest.skip(f"Services not available: {services}")
        
        # Run pipeline twice
        results = []
        for i in range(2):
            collected = self.handler.collect(self.context)
            processed = self.handler.process(self.context, collected)
            vector_chunks = self.handler.chunk_and_embed(self.context, processed)
            
            results.append({
                "text_length": len(collected.get("text", "")),
                "chunk_count": len(vector_chunks),
                "first_embedding": vector_chunks[0].embedding if vector_chunks else None,
            })
        
        # Compare
        text_ratio = min(results[0]["text_length"], results[1]["text_length"]) / max(results[0]["text_length"], results[1]["text_length"]) if max(results[0]["text_length"], results[1]["text_length"]) > 0 else 1
        chunk_match = results[0]["chunk_count"] == results[1]["chunk_count"]
        
        # Embedding similarity
        if results[0]["first_embedding"] is not None and results[1]["first_embedding"] is not None:
            e1 = np.array(results[0]["first_embedding"])
            e2 = np.array(results[1]["first_embedding"])
            emb_sim = float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2)))
        else:
            emb_sim = 0
        
        report.add_metric("text_length_ratio", text_ratio)
        report.add_metric("chunk_count_match", chunk_match)
        report.add_metric("first_embedding_similarity", emb_sim)
        report.add_metric("run1_text_length", results[0]["text_length"])
        report.add_metric("run2_text_length", results[1]["text_length"])
        
        report.print_report()
        
        assert text_ratio > 0.95
        assert emb_sim > 0.95
