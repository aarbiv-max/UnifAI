"""
Unit tests for REMOTE embedding using SentenceTransformerEmbedding with service client.

This test uses the remote embedding service via HTTP.
Requires EMBEDDING_SERVICE_URL environment variable.

Run:
    EMBEDDING_SERVICE_URL=http://embedding-service:5002 \
    pytest tests/embedding/test_embedding_remote.py -v -s
    
The -s flag shows print output for detailed reports.
"""

import os
import time
import pytest
import numpy as np


# Skip all tests if service URL not configured
pytestmark = pytest.mark.skipif(
    not os.environ.get("EMBEDDING_SERVICE_URL"),
    reason="EMBEDDING_SERVICE_URL not set"
)


class TestEmbeddingRemote:
    """Test suite for remote embedding generation with comprehensive reporting."""

    @pytest.fixture(autouse=True)
    def setup(self, embedding_service_url, embedding_service_timeout, embedding_model_name, test_report):
        """Initialize remote embedder for each test."""
        from infrastructure.embedding.sentence_transformer_embedder import SentenceTransformerEmbedding
        from global_utils.clients import EmbeddingServiceClient
        
        self.service_url = embedding_service_url
        self.model_name = embedding_model_name
        
        self.client = EmbeddingServiceClient(
            base_url=embedding_service_url,
            timeout=embedding_service_timeout,
            model_name=embedding_model_name,
        )
        
        self.embedder = SentenceTransformerEmbedding(
            service_client=self.client,
            batch_size=32,
            embedding_dim=384,
        )
        
        self.create_report = test_report

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def test_initialization(self):
        """Test that remote embedder initializes correctly."""
        report = self.create_report(
            "Initialization",
            "remote",
            "Validates SentenceTransformerEmbedding initializes in remote mode with service client"
        )
        
        # Validations
        report.add_validation("embedder_exists", True, self.embedder is not None, self.embedder is not None)
        report.add_validation("is_remote_mode", True, self.embedder.is_remote, self.embedder.is_remote is True)
        report.add_validation("has_service_client", True, self.embedder._service_client is not None, self.embedder._service_client is not None)
        
        # Metrics
        report.add_metric("embedding_dim", self.embedder.embedding_dim)
        report.add_metric("batch_size", self.embedder.batch_size)
        
        # Results
        report.add_result("service_url", self.service_url)
        report.add_result("model_name", self.model_name)
        
        report.print_report()
        
        assert self.embedder is not None
        assert self.embedder.is_remote is True

    def test_service_connection(self):
        """Test connection to the remote service."""
        report = self.create_report(
            "Service Connection",
            "remote",
            "Validates remote embedding service is reachable via /health endpoint"
        )
        
        import requests
        
        try:
            start = time.time()
            response = requests.get(f"{self.service_url}/health", timeout=10)
            elapsed = time.time() - start
            
            is_healthy = response.status_code == 200
            
            report.add_validation("health_check_pass", 200, response.status_code, is_healthy)
            
            report.add_metric("response_time_seconds", elapsed)
            report.add_result("service_url", self.service_url)
            
            report.print_report()
            
            assert response.status_code == 200
            
        except requests.exceptions.ConnectionError as e:
            report.set_failed(f"Cannot connect to service: {str(e)[:100]}")
            report.add_result("service_url", self.service_url)
            report.print_report()
            pytest.skip("Embedding service not available")

    def _check_service(self) -> bool:
        """Check if service is available."""
        import requests
        try:
            resp = requests.get(f"{self.service_url}/health", timeout=10)
            return resp.status_code == 200
        except:
            return False

    def test_single_query_embedding(self):
        """Test generating embedding for a single query."""
        report = self.create_report(
            "Single Query Embedding",
            "remote",
            "Validates single text query produces valid embedding via remote service"
        )
        
        if not self._check_service():
            pytest.skip("Embedding service not available")
        
        query = "What is machine learning?"
        
        start_time = time.time()
        embedding = self.embedder.generate_query_embedding(query)
        elapsed = time.time() - start_time
        
        is_valid_shape = embedding.shape[0] == self.embedder.embedding_dim
        is_non_zero = not np.allclose(embedding, 0)
        
        # Validations
        report.add_validation("embedding_not_none", True, embedding is not None, embedding is not None)
        report.add_validation("correct_dimension", self.embedder.embedding_dim, embedding.shape[0], is_valid_shape)
        report.add_validation("non_zero_values", True, is_non_zero, is_non_zero)
        
        # Metrics
        report.add_metric("embedding_dimension", embedding.shape[0])
        report.add_metric("embedding_norm", float(np.linalg.norm(embedding)))
        report.add_metric("processing_time_seconds", elapsed)
        
        # Results
        report.add_result("query", query)
        report.add_result("embedding_sample", embedding[:5].tolist())
        
        report.print_report()
        
        assert embedding is not None
        assert is_valid_shape

    def test_batch_embedding_generation(self, sample_chunks):
        """Test generating embeddings for multiple chunks."""
        report = self.create_report(
            "Batch Embedding Generation",
            "remote",
            "Validates multiple text chunks are embedded via remote service"
        )
        
        if not self._check_service():
            pytest.skip("Embedding service not available")
        
        start_time = time.time()
        results = self.embedder.generate_embeddings(sample_chunks)
        elapsed = time.time() - start_time
        
        count_match = len(results) == len(sample_chunks)
        all_have_embeddings = all("embedding" in r for r in results)
        
        # Validations
        report.add_validation("output_count_matches", len(sample_chunks), len(results), count_match)
        report.add_validation("all_have_embeddings", True, all_have_embeddings, all_have_embeddings)
        
        # Metrics
        report.add_metric("input_chunk_count", len(sample_chunks))
        report.add_metric("output_chunk_count", len(results))
        report.add_metric("processing_time_seconds", elapsed)
        report.add_metric("chunks_per_second", len(sample_chunks) / elapsed if elapsed > 0 else 0)
        
        # Results
        report.add_result("first_chunk_text", sample_chunks[0]["text"][:50])
        
        report.print_report()
        
        assert count_match
        assert all_have_embeddings

    def test_semantic_similarity(self):
        """Test that similar texts have higher cosine similarity."""
        report = self.create_report(
            "Semantic Similarity",
            "remote",
            "Validates similar texts produce embeddings with higher cosine similarity"
        )
        
        if not self._check_service():
            pytest.skip("Embedding service not available")
        
        similar_pair = (
            "Machine learning is a type of artificial intelligence.",
            "AI and machine learning are closely related technologies."
        )
        dissimilar_pair = (
            "Machine learning is a type of artificial intelligence.",
            "The weather today is sunny and warm."
        )
        
        emb_sim1 = self.embedder.generate_query_embedding(similar_pair[0])
        emb_sim2 = self.embedder.generate_query_embedding(similar_pair[1])
        emb_dis1 = self.embedder.generate_query_embedding(dissimilar_pair[0])
        emb_dis2 = self.embedder.generate_query_embedding(dissimilar_pair[1])
        
        similar_score = self._cosine_similarity(emb_sim1, emb_sim2)
        dissimilar_score = self._cosine_similarity(emb_dis1, emb_dis2)
        
        is_correctly_ordered = similar_score > dissimilar_score
        
        # Validations
        report.add_validation("similar_higher_than_dissimilar", True, is_correctly_ordered, is_correctly_ordered)
        
        # Metrics
        report.add_metric("similar_pair_score", similar_score)
        report.add_metric("dissimilar_pair_score", dissimilar_score)
        report.add_metric("score_difference", similar_score - dissimilar_score)
        
        # Results
        report.add_result("similar_text_1", similar_pair[0][:50])
        report.add_result("similar_text_2", similar_pair[1][:50])
        
        report.print_report()
        
        assert is_correctly_ordered

    def test_embedding_consistency(self):
        """Test that same text produces consistent embedding."""
        report = self.create_report(
            "Embedding Consistency",
            "remote",
            "Validates same text produces similar embedding on multiple runs"
        )
        
        if not self._check_service():
            pytest.skip("Embedding service not available")
        
        text = "This is a test sentence for consistency check."
        
        emb1 = self.embedder.generate_query_embedding(text)
        emb2 = self.embedder.generate_query_embedding(text)
        
        similarity = self._cosine_similarity(emb1, emb2)
        is_consistent = similarity > 0.99  # Allow small floating point differences
        
        # Validations
        report.add_validation("embeddings_consistent", "> 0.99", f"{similarity:.6f}", is_consistent)
        
        # Metrics
        report.add_metric("cosine_similarity", similarity)
        report.add_metric("max_difference", float(np.max(np.abs(emb1 - emb2))))
        
        # Results
        report.add_result("test_text", text)
        
        report.print_report()
        
        assert is_consistent

    def test_empty_input_handling(self):
        """Test handling of empty input."""
        report = self.create_report(
            "Empty Input Handling",
            "remote",
            "Validates empty chunk list returns empty result"
        )
        
        results = self.embedder.generate_embeddings([])
        
        # Validations
        report.add_validation("returns_empty_list", 0, len(results), len(results) == 0)
        
        # Results
        report.add_result("input", [])
        report.add_result("output", results)
        
        report.print_report()
        
        assert results == []

    def test_long_text_handling(self):
        """Test handling of long text input."""
        report = self.create_report(
            "Long Text Handling",
            "remote",
            "Validates long text is processed without error via remote service"
        )
        
        if not self._check_service():
            pytest.skip("Embedding service not available")
        
        long_text = "This is a test sentence. " * 200
        
        start_time = time.time()
        embedding = self.embedder.generate_query_embedding(long_text)
        elapsed = time.time() - start_time
        
        is_valid = embedding is not None and embedding.shape[0] == self.embedder.embedding_dim
        
        # Validations
        report.add_validation("produces_valid_embedding", True, is_valid, is_valid)
        
        # Metrics
        report.add_metric("input_char_count", len(long_text))
        report.add_metric("embedding_dimension", embedding.shape[0])
        report.add_metric("processing_time_seconds", elapsed)
        
        report.print_report()
        
        assert is_valid

    def test_metadata_preservation(self):
        """Test that metadata is preserved in results."""
        report = self.create_report(
            "Metadata Preservation",
            "remote",
            "Validates chunk metadata is preserved after remote embedding"
        )
        
        if not self._check_service():
            pytest.skip("Embedding service not available")
        
        chunks_with_meta = [
            {"text": "First chunk", "id": "1", "source": "doc1"},
            {"text": "Second chunk", "id": "2", "source": "doc2"},
        ]
        
        results = self.embedder.generate_embeddings(chunks_with_meta)
        
        all_preserved = all(
            r.get("id") == c["id"] and r.get("source") == c["source"]
            for r, c in zip(results, chunks_with_meta)
        )
        
        # Validations
        report.add_validation("metadata_preserved", True, all_preserved, all_preserved)
        
        # Results
        report.add_result("input_chunks", chunks_with_meta)
        report.add_result("output_keys", list(results[0].keys()) if results else [])
        
        report.print_report()
        
        assert all_preserved

    def test_performance_benchmark(self, sample_texts):
        """Benchmark remote embedding generation performance."""
        report = self.create_report(
            "Performance Benchmark",
            "remote",
            "Measures remote embedding generation speed and network latency"
        )
        
        if not self._check_service():
            pytest.skip("Embedding service not available")
        
        chunks = [{"text": t, "id": str(i)} for i, t in enumerate(sample_texts * 10)]
        
        start_time = time.time()
        results = self.embedder.generate_embeddings(chunks)
        elapsed = time.time() - start_time
        
        throughput = len(chunks) / elapsed if elapsed > 0 else 0
        
        # Metrics
        report.add_metric("total_chunks", len(chunks))
        report.add_metric("total_time_seconds", elapsed)
        report.add_metric("throughput_chunks_per_second", throughput)
        report.add_metric("avg_time_per_chunk_ms", (elapsed / len(chunks)) * 1000 if chunks else 0)
        
        # Results
        report.add_result("service_url", self.service_url)
        report.add_result("model_name", self.model_name)
        
        report.print_report()
        
        assert len(results) == len(chunks)
