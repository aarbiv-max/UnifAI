"""
End-to-End Test: REMOTE Document Processing → Embedding Pipeline

This test simulates the full pipeline using remote services:
1. Process a document using REMOTE docling service
2. Chunk the extracted text
3. Generate embeddings using REMOTE embedding service

Requires:
    - DOCLING_SERVICE_URL environment variable
    - EMBEDDING_SERVICE_URL environment variable
    - TEST_DOCUMENT_PATH environment variable

Run:
    DOCLING_SERVICE_URL=http://docling-service:5001 \
    EMBEDDING_SERVICE_URL=http://embedding-service:5002 \
    TEST_DOCUMENT_PATH=/path/to/test.pdf \
    pytest tests/e2e/test_e2e_remote.py -v -s
"""

import os
import time
import pytest
import numpy as np
from typing import List, Dict, Any


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


class TestE2ERemote:
    """End-to-end test suite for remote document processing and embedding pipeline."""

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
        """Initialize all remote components."""
        from infrastructure.connector.document_connector import DocumentConnector
        from infrastructure.embedding.sentence_transformer_embedder import SentenceTransformerEmbedding
        from infrastructure.config.doc_config_manager import DocConfigManager
        from global_utils.clients import DoclingServiceClient, EmbeddingServiceClient
        
        # Initialize document connector (remote)
        self.config_manager = DocConfigManager()
        self.docling_client = DoclingServiceClient(
            base_url=docling_service_url,
            timeout=docling_service_timeout,
        )
        self.doc_connector = DocumentConnector(
            config_manager=self.config_manager,
            service_client=self.docling_client,
        )
        
        # Initialize embedder (remote)
        self.embedding_client = EmbeddingServiceClient(
            base_url=embedding_service_url,
            timeout=embedding_service_timeout,
            model_name=embedding_model_name,
        )
        self.embedder = SentenceTransformerEmbedding(
            service_client=self.embedding_client,
            batch_size=32,
            embedding_dim=384,
        )
        
        self.test_document_path = test_document_path
        self.docling_service_url = docling_service_url
        self.embedding_service_url = embedding_service_url
        self.create_report = test_report

    def _simple_chunker(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
        """
        Simple text chunker that splits text into overlapping chunks.
        """
        chunks = []
        words = text.split()
        
        if not words:
            return chunks
        
        words_per_chunk = max(1, chunk_size // 5)
        overlap_words = max(1, overlap // 5)
        
        i = 0
        chunk_id = 0
        
        while i < len(words):
            end_idx = min(i + words_per_chunk, len(words))
            chunk_words = words[i:end_idx]
            chunk_text = " ".join(chunk_words)
            
            chunks.append({
                "text": chunk_text,
                "id": f"chunk_{chunk_id}",
                "start_word": i,
                "end_word": end_idx,
                "char_count": len(chunk_text),
                "word_count": len(chunk_words),
            })
            
            chunk_id += 1
            i = end_idx - overlap_words
            
            if i >= len(words) - overlap_words:
                break
        
        return chunks

    def _check_services(self) -> Dict[str, bool]:
        """Check if both services are available."""
        docling_ok = self.doc_connector.test_connection()
        
        import requests
        try:
            resp = requests.get(f"{self.embedding_service_url}/health", timeout=10)
            embedding_ok = resp.status_code == 200
        except:
            embedding_ok = False
        
        return {"docling": docling_ok, "embedding": embedding_ok}

    def test_pipeline_initialization(self):
        """Test that all pipeline components initialize correctly."""
        report = self.create_report("Pipeline Initialization", "remote")
        
        report.add_metric("doc_connector_is_remote", self.doc_connector.is_remote)
        report.add_metric("embedder_is_remote", self.embedder.is_remote)
        report.add_metric("embedding_dim", self.embedder.embedding_dim)
        report.add_detail("doc_connector_type", type(self.doc_connector).__name__)
        report.add_detail("embedder_type", type(self.embedder).__name__)
        report.add_detail("docling_service_url", self.docling_service_url)
        report.add_detail("embedding_service_url", self.embedding_service_url)
        report.add_detail("mode", "REMOTE")
        
        report.print_report()
        
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
        
        assert services["docling"]
        assert services["embedding"]

    def test_full_pipeline(self):
        """Test the complete document → chunk → embed pipeline via remote services."""
        report = self.create_report("Full Pipeline E2E", "remote")
        
        services = self._check_services()
        if not all(services.values()):
            pytest.skip(f"Services not available: {services}")
        
        total_start = time.time()
        
        # ========== STEP 1: Document Processing (Remote) ==========
        step1_start = time.time()
        doc_result = self.doc_connector.process_document(
            self.test_document_path,
            upload_by="e2e_test"
        )
        step1_time = time.time() - step1_start
        
        text = doc_result.get("text", "")
        markdown = doc_result.get("markdown", "")
        
        report.add_metric("step1_doc_processing_seconds", step1_time)
        report.add_metric("step1_text_length_chars", len(text))
        report.add_metric("step1_text_length_words", len(text.split()))
        report.add_metric("step1_markdown_length_chars", len(markdown))
        
        # ========== STEP 2: Chunking (Local - same as local test) ==========
        step2_start = time.time()
        chunks = self._simple_chunker(text, chunk_size=500, overlap=50)
        step2_time = time.time() - step2_start
        
        report.add_metric("step2_chunking_seconds", step2_time)
        report.add_metric("step2_chunk_count", len(chunks))
        
        if chunks:
            chunk_sizes = [c["char_count"] for c in chunks]
            report.add_metric("step2_avg_chunk_size", np.mean(chunk_sizes))
            report.add_metric("step2_min_chunk_size", np.min(chunk_sizes))
            report.add_metric("step2_max_chunk_size", np.max(chunk_sizes))
        
        # ========== STEP 3: Embedding Generation (Remote) ==========
        step3_start = time.time()
        embedded_chunks = self.embedder.generate_embeddings(chunks)
        step3_time = time.time() - step3_start
        
        report.add_metric("step3_embedding_seconds", step3_time)
        report.add_metric("step3_embedded_chunk_count", len(embedded_chunks))
        
        if embedded_chunks:
            embeddings = [c["embedding"] for c in embedded_chunks]
            norms = [float(np.linalg.norm(e)) for e in embeddings]
            report.add_metric("step3_embedding_dimension", embeddings[0].shape[0])
            report.add_metric("step3_avg_embedding_norm", np.mean(norms))
            report.add_metric("step3_chunks_per_second", len(chunks) / step3_time if step3_time > 0 else 0)
        
        # ========== TOTAL ==========
        total_time = time.time() - total_start
        
        report.add_metric("total_pipeline_seconds", total_time)
        report.add_metric("total_chunks_processed", len(embedded_chunks))
        
        # Network overhead estimation
        network_time = step1_time + step3_time
        report.add_metric("estimated_network_time", network_time)
        report.add_metric("network_overhead_percent", (network_time / total_time) * 100 if total_time > 0 else 0)
        
        # Details
        report.add_detail("input_document", os.path.basename(self.test_document_path))
        report.add_detail("text_preview", text[:200] + "..." if len(text) > 200 else text)
        
        if chunks:
            report.add_detail("first_chunk_text", chunks[0]["text"][:100] + "...")
            report.add_detail("last_chunk_text", chunks[-1]["text"][:100] + "...")
        
        if embedded_chunks:
            report.add_detail("first_embedding_sample", embedded_chunks[0]["embedding"][:5].tolist())
        
        report.print_report()
        
        # Assertions
        assert len(text) > 0, "Document text should not be empty"
        assert len(chunks) > 0, "Should produce at least one chunk"
        assert len(embedded_chunks) == len(chunks), "All chunks should be embedded"
        for chunk in embedded_chunks:
            assert "embedding" in chunk, "Each chunk should have embedding"
            assert chunk["embedding"].shape[0] == self.embedder.embedding_dim

    def test_pipeline_with_query_similarity(self):
        """Test pipeline and query similarity search simulation via remote services."""
        report = self.create_report("Pipeline + Query Similarity", "remote")
        
        services = self._check_services()
        if not all(services.values()):
            pytest.skip(f"Services not available: {services}")
        
        # Process document
        doc_result = self.doc_connector.process_document(self.test_document_path)
        text = doc_result.get("text", "")
        
        # Chunk and embed
        chunks = self._simple_chunker(text, chunk_size=300, overlap=30)
        embedded_chunks = self.embedder.generate_embeddings(chunks)
        
        # Generate query embedding
        query = "What is the main topic of this document?"
        query_embedding = self.embedder.generate_query_embedding(query)
        
        # Calculate similarity with each chunk
        def cosine_sim(a, b):
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        
        similarities = []
        for chunk in embedded_chunks:
            sim = cosine_sim(query_embedding, chunk["embedding"])
            similarities.append({
                "chunk_id": chunk["id"],
                "similarity": sim,
                "text_preview": chunk["text"][:50] + "...",
            })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        report.add_metric("total_chunks", len(embedded_chunks))
        report.add_metric("query_embedding_norm", float(np.linalg.norm(query_embedding)))
        report.add_metric("max_similarity", similarities[0]["similarity"] if similarities else 0)
        report.add_metric("min_similarity", similarities[-1]["similarity"] if similarities else 0)
        report.add_metric("avg_similarity", np.mean([s["similarity"] for s in similarities]) if similarities else 0)
        
        report.add_detail("query", query)
        report.add_detail("top_3_chunks", [
            {"id": s["chunk_id"], "sim": f"{s['similarity']:.4f}", "text": s["text_preview"]}
            for s in similarities[:3]
        ])
        report.add_detail("bottom_3_chunks", [
            {"id": s["chunk_id"], "sim": f"{s['similarity']:.4f}", "text": s["text_preview"]}
            for s in similarities[-3:]
        ])
        
        report.print_report()
        
        assert len(similarities) > 0
        assert similarities[0]["similarity"] > similarities[-1]["similarity"]

    def test_pipeline_chunk_size_variations(self):
        """Test pipeline with different chunk sizes via remote services."""
        report = self.create_report("Chunk Size Variations", "remote")
        
        services = self._check_services()
        if not all(services.values()):
            pytest.skip(f"Services not available: {services}")
        
        doc_result = self.doc_connector.process_document(self.test_document_path)
        text = doc_result.get("text", "")
        
        chunk_configs = [
            {"size": 200, "overlap": 20},
            {"size": 500, "overlap": 50},
            {"size": 1000, "overlap": 100},
        ]
        
        results = []
        for config in chunk_configs:
            chunks = self._simple_chunker(text, chunk_size=config["size"], overlap=config["overlap"])
            
            start = time.time()
            embedded = self.embedder.generate_embeddings(chunks)
            embed_time = time.time() - start
            
            norms = [float(np.linalg.norm(c["embedding"])) for c in embedded]
            
            results.append({
                "chunk_size": config["size"],
                "overlap": config["overlap"],
                "chunk_count": len(chunks),
                "embed_time": embed_time,
                "avg_norm": np.mean(norms) if norms else 0,
            })
        
        for r in results:
            report.add_metric(f"size_{r['chunk_size']}_count", r["chunk_count"])
            report.add_metric(f"size_{r['chunk_size']}_time", r["embed_time"])
            report.add_metric(f"size_{r['chunk_size']}_avg_norm", r["avg_norm"])
        
        report.add_detail("configurations", chunk_configs)
        report.add_detail("results_summary", results)
        
        report.print_report()
        
        assert results[0]["chunk_count"] > results[-1]["chunk_count"]

    def test_pipeline_latency_breakdown(self):
        """Detailed latency breakdown for remote pipeline."""
        report = self.create_report("Latency Breakdown", "remote")
        
        services = self._check_services()
        if not all(services.values()):
            pytest.skip(f"Services not available: {services}")
        
        latencies = {
            "doc_processing": [],
            "chunking": [],
            "embedding": [],
            "total": [],
        }
        
        num_runs = 3
        
        for i in range(num_runs):
            total_start = time.time()
            
            # Document processing
            start = time.time()
            doc_result = self.doc_connector.process_document(self.test_document_path)
            latencies["doc_processing"].append(time.time() - start)
            
            text = doc_result.get("text", "")
            
            # Chunking
            start = time.time()
            chunks = self._simple_chunker(text, chunk_size=400, overlap=40)
            latencies["chunking"].append(time.time() - start)
            
            # Embedding
            start = time.time()
            self.embedder.generate_embeddings(chunks)
            latencies["embedding"].append(time.time() - start)
            
            latencies["total"].append(time.time() - total_start)
        
        # Calculate statistics
        for key, values in latencies.items():
            report.add_metric(f"{key}_avg_seconds", np.mean(values))
            report.add_metric(f"{key}_min_seconds", np.min(values))
            report.add_metric(f"{key}_max_seconds", np.max(values))
            report.add_metric(f"{key}_std_seconds", np.std(values))
        
        # Percentage breakdown
        total_avg = np.mean(latencies["total"])
        report.add_metric("doc_processing_percent", (np.mean(latencies["doc_processing"]) / total_avg) * 100)
        report.add_metric("chunking_percent", (np.mean(latencies["chunking"]) / total_avg) * 100)
        report.add_metric("embedding_percent", (np.mean(latencies["embedding"]) / total_avg) * 100)
        
        report.add_detail("num_runs", num_runs)
        report.add_detail("all_latencies", latencies)
        
        report.print_report()
        
        # Basic sanity check
        assert np.mean(latencies["doc_processing"]) > 0
        assert np.mean(latencies["embedding"]) > 0

    def test_pipeline_consistency(self):
        """Test that remote pipeline produces consistent results."""
        report = self.create_report("Pipeline Consistency", "remote")
        
        services = self._check_services()
        if not all(services.values()):
            pytest.skip(f"Services not available: {services}")
        
        # Run pipeline twice
        results = []
        for i in range(2):
            doc_result = self.doc_connector.process_document(self.test_document_path)
            text = doc_result.get("text", "")
            chunks = self._simple_chunker(text, chunk_size=300, overlap=30)
            embedded = self.embedder.generate_embeddings(chunks)
            
            results.append({
                "text_length": len(text),
                "chunk_count": len(chunks),
                "embedded_count": len(embedded),
                "first_embedding": embedded[0]["embedding"] if embedded else None,
            })
        
        # Compare
        text_length_match = results[0]["text_length"] == results[1]["text_length"]
        chunk_count_match = results[0]["chunk_count"] == results[1]["chunk_count"]
        
        # Text length ratio (should be very close)
        text_ratio = min(results[0]["text_length"], results[1]["text_length"]) / max(results[0]["text_length"], results[1]["text_length"]) if max(results[0]["text_length"], results[1]["text_length"]) > 0 else 1
        
        # Embedding similarity (first chunk)
        if results[0]["first_embedding"] is not None and results[1]["first_embedding"] is not None:
            emb_sim = float(np.dot(results[0]["first_embedding"], results[1]["first_embedding"]) / 
                          (np.linalg.norm(results[0]["first_embedding"]) * np.linalg.norm(results[1]["first_embedding"])))
        else:
            emb_sim = 0
        
        report.add_metric("text_length_match", text_length_match)
        report.add_metric("text_length_ratio", text_ratio)
        report.add_metric("chunk_count_match", chunk_count_match)
        report.add_metric("first_embedding_similarity", emb_sim)
        report.add_metric("run1_text_length", results[0]["text_length"])
        report.add_metric("run2_text_length", results[1]["text_length"])
        report.add_metric("run1_chunks", results[0]["chunk_count"])
        report.add_metric("run2_chunks", results[1]["chunk_count"])
        
        report.print_report()
        
        # Remote services might have slight variations
        assert text_ratio > 0.95, "Text extraction should be consistent"
        assert emb_sim > 0.95, "Embeddings should be consistent"
