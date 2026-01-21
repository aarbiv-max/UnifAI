"""
Unit tests for LOCAL embedding using SentenceTransformerEmbedding.

This test uses the local SentenceTransformers library directly.
No external service is required.

Run:
    pytest tests/embedding/test_embedding_local.py -v -s
    
The -s flag shows print output for detailed reports.
"""

import time
import pytest
import numpy as np


class TestEmbeddingLocal:
    """Test suite for local embedding generation with comprehensive reporting."""

    @pytest.fixture(autouse=True)
    def setup(self, embedding_model_name, test_report):
        """Initialize local embedder for each test."""
        from infrastructure.embedding.sentence_transformer_embedder import SentenceTransformerEmbedding
        
        self.embedder = SentenceTransformerEmbedding(
            model_name=embedding_model_name,
            batch_size=32,
            device="cpu",
        )
        self.model_name = embedding_model_name
        self.create_report = test_report

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def test_initialization(self):
        """Test that local embedder initializes correctly."""
        report = self.create_report(
            "Initialization",
            "local",
            "Validates SentenceTransformerEmbedding initializes in local mode"
        )
        
        # Validations
        report.add_validation("embedder_exists", True, self.embedder is not None, self.embedder is not None)
        report.add_validation("is_local_mode", False, self.embedder.is_remote, self.embedder.is_remote is False)
        report.add_validation("embedding_dim_valid", "> 0", self.embedder.embedding_dim, self.embedder.embedding_dim > 0)
        report.add_validation("model_loaded", True, self.embedder._model is not None, self.embedder._model is not None)
        
        # Metrics
        report.add_metric("embedding_dim", self.embedder.embedding_dim)
        report.add_metric("batch_size", self.embedder.batch_size)
        
        # Results
        report.add_result("model_name", self.model_name)
        
        report.print_report()
        
        assert self.embedder is not None
        assert self.embedder.is_remote is False
        assert self.embedder.embedding_dim > 0

    def test_single_query_embedding(self):
        """Test generating embedding for a single query."""
        report = self.create_report(
            "Single Query Embedding",
            "local",
            "Validates single text query produces valid embedding vector"
        )
        
        query = "What is machine learning?"
        
        start_time = time.time()
        embedding = self.embedder.generate_query_embedding(query)
        elapsed = time.time() - start_time
        
        is_valid_shape = embedding.shape == (self.embedder.embedding_dim,)
        is_non_zero = not np.allclose(embedding, 0)
        
        # Validations
        report.add_validation("embedding_not_none", True, embedding is not None, embedding is not None)
        report.add_validation("correct_dimension", self.embedder.embedding_dim, embedding.shape[0], is_valid_shape)
        report.add_validation("non_zero_values", True, is_non_zero, is_non_zero)
        
        # Metrics
        report.add_metric("embedding_dimension", embedding.shape[0])
        report.add_metric("embedding_norm", float(np.linalg.norm(embedding)))
        report.add_metric("embedding_mean", float(np.mean(embedding)))
        report.add_metric("processing_time_seconds", elapsed)
        
        # Results
        report.add_result("query", query)
        report.add_result("embedding_sample", embedding[:5].tolist())
        
        report.print_report()
        
        assert embedding is not None
        assert is_valid_shape
        assert is_non_zero

    def test_batch_embedding_generation(self, sample_chunks):
        """Test generating embeddings for multiple chunks."""
        report = self.create_report(
            "Batch Embedding Generation",
            "local",
            "Validates multiple text chunks are embedded in batch"
        )
        
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
        
        # Embedding statistics
        embeddings = [r["embedding"] for r in results]
        norms = [float(np.linalg.norm(e)) for e in embeddings]
        report.add_metric("avg_embedding_norm", np.mean(norms))
        
        # Results
        report.add_result("first_chunk_text", sample_chunks[0]["text"][:50])
        
        report.print_report()
        
        assert count_match
        assert all_have_embeddings

    def test_semantic_similarity(self, sample_texts):
        """Test that similar texts have higher cosine similarity."""
        report = self.create_report(
            "Semantic Similarity",
            "local",
            "Validates similar texts produce embeddings with higher cosine similarity"
        )
        
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
        report.add_validation("similar_score_reasonable", "> 0.5", f"{similar_score:.3f}", similar_score > 0.5)
        
        # Metrics
        report.add_metric("similar_pair_score", similar_score)
        report.add_metric("dissimilar_pair_score", dissimilar_score)
        report.add_metric("score_difference", similar_score - dissimilar_score)
        
        # Results
        report.add_result("similar_text_1", similar_pair[0][:50])
        report.add_result("similar_text_2", similar_pair[1][:50])
        report.add_result("dissimilar_text", dissimilar_pair[1][:50])
        
        report.print_report()
        
        assert is_correctly_ordered

    def test_embedding_consistency(self):
        """Test that same text produces same embedding."""
        report = self.create_report(
            "Embedding Consistency",
            "local",
            "Validates same text produces identical embedding on multiple runs"
        )
        
        text = "This is a test sentence for consistency check."
        
        emb1 = self.embedder.generate_query_embedding(text)
        emb2 = self.embedder.generate_query_embedding(text)
        
        similarity = self._cosine_similarity(emb1, emb2)
        is_identical = np.allclose(emb1, emb2, rtol=1e-5)
        
        # Validations
        report.add_validation("embeddings_identical", True, is_identical, is_identical)
        report.add_validation("similarity_score", 1.0, f"{similarity:.6f}", similarity > 0.9999)
        
        # Metrics
        report.add_metric("cosine_similarity", similarity)
        report.add_metric("max_difference", float(np.max(np.abs(emb1 - emb2))))
        
        # Results
        report.add_result("test_text", text)
        
        report.print_report()
        
        assert is_identical

    def test_empty_input_handling(self):
        """Test handling of empty input."""
        report = self.create_report(
            "Empty Input Handling",
            "local",
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
            "local",
            "Validates long text is processed without error"
        )
        
        long_text = "This is a test sentence. " * 200
        
        start_time = time.time()
        embedding = self.embedder.generate_query_embedding(long_text)
        elapsed = time.time() - start_time
        
        is_valid = embedding is not None and embedding.shape[0] == self.embedder.embedding_dim
        
        # Validations
        report.add_validation("produces_valid_embedding", True, is_valid, is_valid)
        
        # Metrics
        report.add_metric("input_char_count", len(long_text))
        report.add_metric("input_word_count", len(long_text.split()))
        report.add_metric("embedding_dimension", embedding.shape[0])
        report.add_metric("processing_time_seconds", elapsed)
        
        report.print_report()
        
        assert is_valid

    def test_special_characters(self):
        """Test handling of special characters."""
        report = self.create_report(
            "Special Characters",
            "local",
            "Validates text with special characters is processed correctly"
        )
        
        special_text = "Test with émojis 🎉 and spëcial çharacters: @#$%^&*()"
        
        embedding = self.embedder.generate_query_embedding(special_text)
        
        is_valid = embedding is not None and not np.allclose(embedding, 0)
        
        # Validations
        report.add_validation("produces_valid_embedding", True, is_valid, is_valid)
        
        # Metrics
        report.add_metric("embedding_dimension", embedding.shape[0])
        report.add_metric("embedding_norm", float(np.linalg.norm(embedding)))
        
        # Results
        report.add_result("input_text", special_text)
        
        report.print_report()
        
        assert is_valid

    def test_metadata_preservation(self, sample_chunks):
        """Test that metadata is preserved in results."""
        report = self.create_report(
            "Metadata Preservation",
            "local",
            "Validates chunk metadata is preserved after embedding"
        )
        
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

    def test_embedding_normalization(self):
        """Test embedding normalization properties."""
        report = self.create_report(
            "Embedding Normalization",
            "local",
            "Validates embedding vectors have consistent normalization"
        )
        
        texts = [
            "Short text",
            "A medium length text with more words",
            "A very long text " * 20,
        ]
        
        embeddings = [self.embedder.generate_query_embedding(t) for t in texts]
        norms = [float(np.linalg.norm(e)) for e in embeddings]
        
        norm_variance = np.var(norms)
        avg_norm = np.mean(norms)
        
        # Check if norms are approximately 1 (normalized)
        are_normalized = all(0.9 < n < 1.1 for n in norms)
        
        # Validations
        report.add_validation("consistent_norms", "low variance", f"{norm_variance:.6f}", norm_variance < 0.1)
        
        # Metrics
        for i, (text, norm) in enumerate(zip(texts, norms)):
            report.add_metric(f"text_{i}_norm", norm)
        report.add_metric("norm_variance", norm_variance)
        report.add_metric("avg_norm", avg_norm)
        
        # Results
        report.add_result("are_unit_normalized", are_normalized)
        
        report.print_report()

    def test_performance_benchmark(self, sample_texts):
        """Benchmark embedding generation performance."""
        report = self.create_report(
            "Performance Benchmark",
            "local",
            "Measures embedding generation speed and throughput"
        )
        
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
        report.add_result("model_name", self.model_name)
        report.add_result("batch_size", self.embedder.batch_size)
        
        report.print_report()
        
        assert len(results) == len(chunks)
