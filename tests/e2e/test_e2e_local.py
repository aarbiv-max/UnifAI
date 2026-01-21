"""
End-to-End Test: LOCAL Document Processing → Embedding Pipeline

This test simulates the full pipeline:
1. Process a document using LOCAL docling library
2. Chunk the extracted text
3. Generate embeddings using LOCAL SentenceTransformer model

Requires TEST_DOCUMENT_PATH environment variable.

Run:
    TEST_DOCUMENT_PATH=/path/to/test.pdf pytest tests/e2e/test_e2e_local.py -v -s
"""

import os
import time
import pytest
import numpy as np
from typing import List, Dict, Any


# Skip all tests if test document not configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DOCUMENT_PATH") or not os.path.exists(os.environ.get("TEST_DOCUMENT_PATH", "")),
    reason="TEST_DOCUMENT_PATH not set or file does not exist"
)


class TestE2ELocal:
    """End-to-end test suite for local document processing and embedding pipeline."""

    @pytest.fixture(autouse=True)
    def setup(self, test_document_path, embedding_model_name, test_report):
        """Initialize all local components."""
        from infrastructure.connector.document_connector import DocumentConnector
        from infrastructure.embedding.sentence_transformer_embedder import SentenceTransformerEmbedding
        from infrastructure.config.doc_config_manager import DocConfigManager
        
        # Initialize document connector (local)
        self.config_manager = DocConfigManager()
        self.doc_connector = DocumentConnector(config_manager=self.config_manager)
        
        # Initialize embedder (local)
        self.embedder = SentenceTransformerEmbedding(
            model_name=embedding_model_name,
            batch_size=32,
            device="cpu",
        )
        
        self.test_document_path = test_document_path
        self.create_report = test_report

    def _simple_chunker(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
        """
        Simple text chunker that splits text into overlapping chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Target size of each chunk in characters
            overlap: Number of overlapping characters between chunks
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        chunks = []
        words = text.split()
        
        if not words:
            return chunks
        
        # Approximate words per chunk (assuming avg 5 chars per word)
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

    def test_pipeline_initialization(self):
        """Test that all pipeline components initialize correctly."""
        report = self.create_report("Pipeline Initialization", "local")
        
        report.add_metric("doc_connector_is_remote", self.doc_connector.is_remote)
        report.add_metric("embedder_is_remote", self.embedder.is_remote)
        report.add_metric("embedding_dim", self.embedder.embedding_dim)
        report.add_detail("doc_connector_type", type(self.doc_connector).__name__)
        report.add_detail("embedder_type", type(self.embedder).__name__)
        report.add_detail("mode", "LOCAL")
        
        report.print_report()
        
        assert self.doc_connector.is_remote is False
        assert self.embedder.is_remote is False

    def test_full_pipeline(self):
        """Test the complete document → chunk → embed pipeline."""
        report = self.create_report("Full Pipeline E2E", "local")
        
        total_start = time.time()
        
        # ========== STEP 1: Document Processing ==========
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
        
        # ========== STEP 2: Chunking ==========
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
        
        # ========== STEP 3: Embedding Generation ==========
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
        """Test pipeline and query similarity search simulation."""
        report = self.create_report("Pipeline + Query Similarity", "local")
        
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
        """Test pipeline with different chunk sizes."""
        report = self.create_report("Chunk Size Variations", "local")
        
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
        
        # Smaller chunks should produce more chunks
        assert results[0]["chunk_count"] > results[-1]["chunk_count"]

    def test_pipeline_multiple_documents_simulation(self):
        """Simulate processing multiple documents (same doc multiple times)."""
        report = self.create_report("Multi-Document Simulation", "local")
        
        num_iterations = 3
        all_results = []
        
        total_start = time.time()
        
        for i in range(num_iterations):
            iter_start = time.time()
            
            # Process
            doc_result = self.doc_connector.process_document(self.test_document_path)
            text = doc_result.get("text", "")
            
            # Chunk
            chunks = self._simple_chunker(text, chunk_size=400, overlap=40)
            
            # Embed
            embedded = self.embedder.generate_embeddings(chunks)
            
            iter_time = time.time() - iter_start
            
            all_results.append({
                "iteration": i + 1,
                "text_length": len(text),
                "chunk_count": len(chunks),
                "embedded_count": len(embedded),
                "time_seconds": iter_time,
            })
        
        total_time = time.time() - total_start
        
        report.add_metric("total_iterations", num_iterations)
        report.add_metric("total_time_seconds", total_time)
        report.add_metric("avg_time_per_iteration", total_time / num_iterations)
        
        total_chunks = sum(r["chunk_count"] for r in all_results)
        report.add_metric("total_chunks_processed", total_chunks)
        report.add_metric("overall_chunks_per_second", total_chunks / total_time if total_time > 0 else 0)
        
        for r in all_results:
            report.add_metric(f"iter_{r['iteration']}_time", r["time_seconds"])
            report.add_metric(f"iter_{r['iteration']}_chunks", r["chunk_count"])
        
        report.add_detail("all_iterations", all_results)
        
        report.print_report()
        
        # All iterations should produce same results
        assert all(r["chunk_count"] == all_results[0]["chunk_count"] for r in all_results)

    def test_pipeline_embedding_consistency(self):
        """Test that the same document produces consistent embeddings."""
        report = self.create_report("Embedding Consistency", "local")
        
        # Process document
        doc_result = self.doc_connector.process_document(self.test_document_path)
        text = doc_result.get("text", "")
        chunks = self._simple_chunker(text, chunk_size=300, overlap=30)
        
        # Embed twice
        embedded1 = self.embedder.generate_embeddings(chunks.copy())
        embedded2 = self.embedder.generate_embeddings(chunks.copy())
        
        # Compare embeddings
        differences = []
        for e1, e2 in zip(embedded1, embedded2):
            diff = np.abs(e1["embedding"] - e2["embedding"])
            differences.append({
                "max_diff": float(np.max(diff)),
                "mean_diff": float(np.mean(diff)),
                "identical": np.allclose(e1["embedding"], e2["embedding"]),
            })
        
        all_identical = all(d["identical"] for d in differences)
        max_diff_overall = max(d["max_diff"] for d in differences)
        
        report.add_metric("chunks_compared", len(differences))
        report.add_metric("all_identical", all_identical)
        report.add_metric("max_difference_overall", max_diff_overall)
        report.add_metric("avg_max_difference", np.mean([d["max_diff"] for d in differences]))
        
        report.add_detail("comparison_summary", differences[:5])
        
        report.print_report()
        
        assert all_identical, "Embeddings should be deterministic"
