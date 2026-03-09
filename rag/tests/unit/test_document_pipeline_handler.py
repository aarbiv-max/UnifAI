"""Unit tests for DocumentPipelineHandler."""
from unittest.mock import MagicMock, patch, PropertyMock
import numpy as np

import pytest

from core.pipeline.domain.port import PipelineContext
from core.data_sources.types.document.pipeline_handler import DocumentPipelineHandler
from core.vector.domain.model import VectorChunk


def _build_context(**overrides):
    defaults = dict(
        pipeline_id="pipe_1",
        source_type="DOCUMENT",
        source_id="src_1",
        source_name="report.pdf",
        metadata={"doc_path": "/tmp/report.pdf", "upload_by": "alice"},
    )
    defaults.update(overrides)
    return PipelineContext(**defaults)


@pytest.mark.unit
@pytest.mark.document
@pytest.mark.pipeline
class TestDocumentPipelineHandler:

    @pytest.fixture
    def mocks(self):
        connector = MagicMock()
        processor = MagicMock()
        chunker = MagicMock()
        embedder = MagicMock()
        return connector, processor, chunker, embedder

    @pytest.fixture
    def handler(self, mocks):
        connector, processor, chunker, embedder = mocks
        return DocumentPipelineHandler(
            connector=connector,
            processor=processor,
            chunker=chunker,
            embedder=embedder,
        )

    # ── source_type ───────────────────────────────────────────────────────

    def test_source_type_is_document(self, handler):
        assert handler.source_type == "DOCUMENT"

    # ── collect ───────────────────────────────────────────────────────────

    def test_collect_calls_connector(self, handler, mocks):
        connector = mocks[0]
        processed_doc = MagicMock()
        processed_doc.to_dict.return_value = {"text": "hello"}
        connector.process_document.return_value = processed_doc

        ctx = _build_context()
        result = handler.collect(ctx)

        connector.process_document.assert_called_once_with(
            document_path="/tmp/report.pdf",
            upload_by="alice",
        )
        assert result == {"text": "hello"}

    def test_collect_caches_result(self, handler, mocks):
        connector = mocks[0]
        processed_doc = MagicMock()
        processed_doc.to_dict.return_value = {}
        connector.process_document.return_value = processed_doc

        ctx = _build_context()
        handler.collect(ctx)

        assert handler._cached_collected is processed_doc

    # ── process ───────────────────────────────────────────────────────────

    def test_process_calls_processor_with_correct_flags(self, handler, mocks):
        processor = mocks[1]
        processor.process.return_value = {"text": "processed"}

        ctx = _build_context()
        raw = {"text": "raw"}
        handler.process(ctx, raw)

        processor.process.assert_called_once_with(
            raw,
            clean_markdown=False,
            clean_text=False,
            remove_references=False,
            preserve_original=True,
        )

    # ── chunk_and_embed ───────────────────────────────────────────────────

    def test_chunk_and_embed_enriches_metadata(self, handler, mocks):
        processor, chunker, embedder = mocks[1], mocks[2], mocks[3]
        processor.prepare_for_single_doc_embedding.return_value = {"text": "ready"}
        chunker.chunk_content.return_value = [
            {"text": "chunk1", "metadata": {}},
            {"text": "chunk2", "metadata": {"existing_key": "val"}},
        ]
        embedder.generate_embeddings.return_value = [
            {"text": "chunk1", "embedding": [0.1, 0.2], "metadata": {"source_id": "src_1", "source_type": "DOCUMENT"}},
            {"text": "chunk2", "embedding": [0.3, 0.4], "metadata": {"existing_key": "val", "source_id": "src_1", "source_type": "DOCUMENT"}},
        ]

        ctx = _build_context()
        result = handler.chunk_and_embed(ctx, {"text": "processed"})

        for chunk in result:
            assert chunk.metadata["source_id"] == "src_1"
            assert chunk.metadata["source_type"] == "DOCUMENT"

    def test_chunk_and_embed_converts_numpy_embedding(self, handler, mocks):
        processor, chunker, embedder = mocks[1], mocks[2], mocks[3]
        processor.prepare_for_single_doc_embedding.return_value = {"text": "ready"}
        chunker.chunk_content.return_value = [{"text": "c1", "metadata": {}}]

        numpy_arr = np.array([0.1, 0.2, 0.3])
        embedder.generate_embeddings.return_value = [
            {"text": "c1", "embedding": numpy_arr, "metadata": {"source_id": "src_1", "source_type": "DOCUMENT"}},
        ]

        ctx = _build_context()
        result = handler.chunk_and_embed(ctx, {"text": "processed"})

        assert isinstance(result[0].embedding, list)
        assert result[0].embedding == [0.1, 0.2, 0.3]

    def test_chunk_and_embed_handles_list_embedding(self, handler, mocks):
        processor, chunker, embedder = mocks[1], mocks[2], mocks[3]
        processor.prepare_for_single_doc_embedding.return_value = {"text": "ready"}
        chunker.chunk_content.return_value = [{"text": "c1", "metadata": {}}]
        embedder.generate_embeddings.return_value = [
            {"text": "c1", "embedding": [0.4, 0.5], "metadata": {"source_id": "src_1", "source_type": "DOCUMENT"}},
        ]

        ctx = _build_context()
        result = handler.chunk_and_embed(ctx, {"text": "processed"})

        assert result[0].embedding == [0.4, 0.5]

    def test_chunk_and_embed_returns_vector_chunks(self, handler, mocks):
        processor, chunker, embedder = mocks[1], mocks[2], mocks[3]
        processor.prepare_for_single_doc_embedding.return_value = {"text": "ready"}
        chunker.chunk_content.return_value = [{"text": "c1", "metadata": {}}]
        embedder.generate_embeddings.return_value = [
            {"text": "c1", "embedding": [0.1], "metadata": {"source_id": "src_1", "source_type": "DOCUMENT"}},
        ]

        ctx = _build_context()
        result = handler.chunk_and_embed(ctx, {"text": "processed"})

        assert all(isinstance(c, VectorChunk) for c in result)

    # ── get_summary ───────────────────────────────────────────────────────

    def test_get_summary_with_cached_document(self, handler, mocks):
        cached = MagicMock()
        cached.metadata = {"page_count": 5, "file_size": 1024}
        cached.text = "full document text"
        handler._cached_collected = cached

        ctx = _build_context()
        summary = handler.get_summary(ctx, {})

        assert summary["page_count"] == 5
        assert summary["full_text"] == "full document text"
        assert summary["file_size"] == 1024

    def test_get_summary_without_cached_document(self, handler):
        ctx = _build_context()
        summary = handler.get_summary(ctx, {})

        assert summary == {"page_count": 0, "full_text": "", "file_size": 0}

    # ── cleanup ───────────────────────────────────────────────────────────

    @patch("core.data_sources.types.document.pipeline_handler.cleanup_file", return_value=True)
    def test_cleanup_with_doc_path(self, mock_cleanup, handler):
        ctx = _build_context()
        result = handler.cleanup(ctx)

        mock_cleanup.assert_called_once_with("/tmp/report.pdf", "after pipeline completion")
        assert result is True

    def test_cleanup_without_doc_path(self, handler):
        ctx = _build_context(metadata={})
        result = handler.cleanup(ctx)
        assert result is False
