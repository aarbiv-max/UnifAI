"""Unit tests for PipelineExecutor orchestration."""
from unittest.mock import MagicMock, PropertyMock

import pytest

from core.pipeline.domain.model import PipelineStatus
from core.pipeline.domain.port import PipelineContext
from core.pipeline.executor import PipelineExecutor


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
class TestPipelineExecutor:

    @pytest.fixture
    def deps(self):
        """Shared mock dependencies for every test."""
        pipeline_svc = MagicMock()
        monitoring_svc = MagicMock()
        data_source_svc = MagicMock()
        vector_repo = MagicMock()
        vector_repo_factory = MagicMock(return_value=vector_repo)

        handler = MagicMock()
        type(handler).source_type = PropertyMock(return_value="DOCUMENT")
        handler.collect.return_value = {"text": "hello"}
        handler.process.return_value = {"text": "processed"}
        handler.chunk_and_embed.return_value = [MagicMock()]
        handler.get_summary.return_value = {"page_count": 1}

        executor = PipelineExecutor(
            pipeline_service=pipeline_svc,
            monitoring_service=monitoring_svc,
            data_source_service=data_source_svc,
            vector_repository=vector_repo_factory,
        )
        return {
            "executor": executor,
            "handler": handler,
            "pipeline_svc": pipeline_svc,
            "monitoring_svc": monitoring_svc,
            "data_source_svc": data_source_svc,
            "vector_repo": vector_repo,
        }

    # ── Happy path ────────────────────────────────────────────────────────

    def test_happy_path_status_transitions(self, deps):
        ctx = _build_context()
        deps["executor"].execute(deps["handler"], ctx)

        status_calls = [
            c.args[1] for c in deps["pipeline_svc"].update_status.call_args_list
        ]
        assert status_calls == [
            PipelineStatus.COLLECTING,
            PipelineStatus.PROCESSING,
            PipelineStatus.CHUNKING_AND_EMBEDDING,
            PipelineStatus.STORING,
            PipelineStatus.DONE,
        ]

    def test_happy_path_stores_embeddings(self, deps):
        ctx = _build_context()
        deps["executor"].execute(deps["handler"], ctx)

        deps["vector_repo"].store.assert_called_once_with(
            deps["handler"].chunk_and_embed.return_value
        )

    def test_happy_path_upserts_source_with_summary(self, deps):
        ctx = _build_context()
        deps["executor"].execute(deps["handler"], ctx)

        deps["data_source_svc"].upsert_after_pipeline.assert_called_once_with(
            source_id="src_1",
            source_name="report.pdf",
            source_type="DOCUMENT",
            pipeline_id="pipe_1",
            summary={"page_count": 1},
        )

    # ── Failure at each step ──────────────────────────────────────────────

    def _assert_failure_at_step(self, deps, step_method, expected_failed_at):
        getattr(deps["handler"], step_method).side_effect = RuntimeError("boom")
        ctx = _build_context()

        with pytest.raises(RuntimeError, match="boom"):
            deps["executor"].execute(deps["handler"], ctx)

        deps["monitoring_svc"].record_error.assert_called_once()
        error_details = deps["monitoring_svc"].record_error.call_args.kwargs.get(
            "error_details"
        ) or deps["monitoring_svc"].record_error.call_args[1].get("error_details")
        assert error_details["failed_at"] == expected_failed_at

        deps["pipeline_svc"].update_status.assert_any_call(
            "pipe_1", PipelineStatus.FAILED
        )

    def test_failure_at_collect_records_error(self, deps):
        self._assert_failure_at_step(deps, "collect", "COLLECTING")

    def test_failure_at_process_records_error(self, deps):
        self._assert_failure_at_step(deps, "process", "PROCESSING")

    def test_failure_at_chunk_and_embed_records_error(self, deps):
        self._assert_failure_at_step(deps, "chunk_and_embed", "CHUNKING_AND_EMBEDDING")

    def test_failure_at_store_records_error(self, deps):
        deps["vector_repo"].store.side_effect = RuntimeError("store boom")
        ctx = _build_context()

        with pytest.raises(RuntimeError, match="store boom"):
            deps["executor"].execute(deps["handler"], ctx)

        error_details = deps["monitoring_svc"].record_error.call_args.kwargs.get(
            "error_details"
        ) or deps["monitoring_svc"].record_error.call_args[1].get("error_details")
        assert error_details["failed_at"] == "STORING"

    # ── Failure upserts error summary ─────────────────────────────────────

    def test_failure_upserts_source_with_error_info(self, deps):
        deps["handler"].collect.side_effect = ValueError("bad data")
        ctx = _build_context()

        with pytest.raises(ValueError):
            deps["executor"].execute(deps["handler"], ctx)

        upsert_call = deps["data_source_svc"].upsert_after_pipeline
        upsert_call.assert_called_once()
        summary = upsert_call.call_args.kwargs.get("summary") or upsert_call.call_args[1].get("summary")
        assert "bad data" in summary["last_error"]
        assert summary["failed_at"] == "COLLECTING"

    # ── Cleanup guarantees ────────────────────────────────────────────────

    def test_cleanup_always_called_on_success(self, deps):
        ctx = _build_context()
        deps["executor"].execute(deps["handler"], ctx)

        deps["handler"].cleanup.assert_called_once_with(ctx)
        deps["monitoring_svc"].finish_log_monitoring.assert_called_once()

    def test_cleanup_always_called_on_failure(self, deps):
        deps["handler"].collect.side_effect = RuntimeError("fail")
        ctx = _build_context()

        with pytest.raises(RuntimeError):
            deps["executor"].execute(deps["handler"], ctx)

        deps["handler"].cleanup.assert_called_once_with(ctx)
        deps["monitoring_svc"].finish_log_monitoring.assert_called_once()

    # ── Exception propagation ─────────────────────────────────────────────

    def test_exception_re_raised(self, deps):
        deps["handler"].process.side_effect = TypeError("wrong type")
        ctx = _build_context()

        with pytest.raises(TypeError, match="wrong type"):
            deps["executor"].execute(deps["handler"], ctx)

    # ── Monitoring setup ──────────────────────────────────────────────────

    def test_monitoring_started_with_correct_pipeline_id(self, deps):
        ctx = _build_context()
        deps["executor"].execute(deps["handler"], ctx)

        deps["monitoring_svc"].start_log_monitoring.assert_called_once()
        call_kwargs = deps["monitoring_svc"].start_log_monitoring.call_args
        pipeline_id_arg = call_kwargs.kwargs.get("pipeline_id") or call_kwargs[1].get("pipeline_id")
        assert pipeline_id_arg == "document_src_1"
