"""
End-to-End Stress Test for Document Upload and Embedding Pipeline.

Validates the RAG system's ability to handle concurrent document uploads and
embedding pipeline execution under load.

Test Cases:
1. test_concurrent_document_upload      - uploads N docs concurrently, checks success rate
2. test_embedding_pipeline_execution    - triggers embed pipeline and monitors Celery tasks
3. test_full_upload_and_embed_flow      - full end-to-end upload → embed → verify flow

Run with:
    pytest tests/e2e/test_doc_upload_stress.py -v -s
    pytest tests/e2e/test_doc_upload_stress.py -v -s \\
        --api-base-url http://myserver/api \\
        --num-docs 50 \\
        --concurrent-uploads 5
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from typing import List, Tuple

from tests.base.base_e2e_test import BaseE2ETest
from tests.factories.document_factory import DocumentFactory
from tests.fixtures.common.api_fixtures import RagTestConfig
from tests.docs.stress_test_doc_upload import (
    CeleryMonitor,
    EmbeddingStats,
    StressTestRunner,
    UploadStats,
)


# =============================================================================
# HELPERS
# =============================================================================

def _run_async(coro):
    """Run an async coroutine from synchronous pytest test methods."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _build_runner(rag_config: RagTestConfig) -> StressTestRunner:
    """Construct a StressTestRunner from a RagTestConfig."""

    class _Cfg:
        API_BASE_URL = rag_config.api_base_url
        UPLOAD_ENDPOINT = rag_config.upload_endpoint
        EMBED_ENDPOINT = rag_config.embed_endpoint
        MONGODB_HOST = rag_config.mongodb_host
        MONGODB_PORT = rag_config.mongodb_port
        MONGODB_DB = rag_config.mongodb_db
        NUM_DOCUMENTS = rag_config.num_documents
        CONCURRENT_UPLOADS = rag_config.concurrent_uploads
        PAGES_PER_DOC = rag_config.pages_per_doc
        UPLOAD_TIMEOUT = rag_config.upload_timeout
        CELERY_MONITOR_TIMEOUT = rag_config.celery_monitor_timeout
        CELERY_POLL_INTERVAL = rag_config.celery_poll_interval
        TEST_USER = rag_config.test_user

    return StressTestRunner(_Cfg())


def _count_relevant_completed_tasks(monitor: CeleryMonitor, since: datetime) -> int:
    """Count completed tasks with pipeline_id starting with 'document_'.

    Uses the same filtering logic as monitor_celery_tasks so the count is
    directly comparable.
    """
    tasks = monitor.get_recent_tasks(since)
    count = 0
    for task in tasks:
        result = task.get('result', {})
        if result:
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    continue
            if isinstance(result, dict):
                pid = result.get('pipeline_id', '')
                if isinstance(pid, str) and pid.startswith('document_'):
                    count += 1
    return count


# =============================================================================
# TEST CLASS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.stress
@pytest.mark.document
@pytest.mark.rag
class TestDocumentUploadStress(BaseE2ETest):
    """End-to-end stress tests for RAG document upload and embedding pipeline.

    Each test method targets one phase of the pipeline so that failures are
    reported with fine-grained granularity (upload vs. embedding vs. full flow).

    The ``batch_pdf_documents`` fixture is session-scoped so PDFs are
    generated once and reused across all three tests.
    """

    # ------------------------------------------------------------------
    # Test 1 – Upload phase only
    # ------------------------------------------------------------------

    @pytest.mark.slow
    def test_concurrent_document_upload(
        self,
        rag_config: RagTestConfig,
        batch_pdf_documents: List[Tuple[int, str, bytes]],
        capsys,
    ):
        """Upload all documents concurrently and assert success rate >= 95 %.

        This test covers Phase 1 of the pipeline:
        - Generates N unique PDF documents (via batch_pdf_documents fixture)
        - Uploads them in batches of CONCURRENT_UPLOADS
        - Asserts that at least 95 % of uploads succeed
        - Asserts average upload time does not exceed 30 s
        """
        runner = _build_runner(rag_config)

        # Pre-populate runner with the fixture's documents
        runner.document_filenames = [fname for _, fname, _ in batch_pdf_documents]

        # Run upload phase using the pre-generated docs directly
        async def _upload():
            import aiohttp

            runner.upload_stats.start_time = __import__("time").time()
            async with aiohttp.ClientSession() as session:
                for i in range(0, len(batch_pdf_documents), rag_config.concurrent_uploads):
                    batch = batch_pdf_documents[i: i + rag_config.concurrent_uploads]
                    await runner.upload_batch(session, batch)
            runner.upload_stats.end_time = __import__("time").time()

        _run_async(_upload())

        # Print report
        empty_embed = EmbeddingStats()
        with capsys.disabled():
            print(self.build_report_lines(runner.upload_stats, empty_embed))

        # Assertions
        self.assert_upload_success_rate(runner.upload_stats, min_rate=95.0)
        self.assert_avg_upload_time(runner.upload_stats, max_seconds=30.0)

    # ------------------------------------------------------------------
    # Test 2 – Embedding pipeline phase only
    # ------------------------------------------------------------------

    @pytest.mark.slow
    def test_embedding_pipeline_execution(
        self,
        rag_config: RagTestConfig,
        batch_pdf_documents: List[Tuple[int, str, bytes]],
        celery_monitor,
        capsys,
    ):
        """Trigger the embedding pipeline and assert Celery tasks complete.

        This test covers Phase 2 of the pipeline:
        - Assumes documents are already uploaded (or uploads them first if needed)
        - Triggers PUT /api/pipelines/embed
        - Monitors Celery tasks via MongoDB
        - Asserts no task failures and success rate >= 95 %

        Note: Run after test_concurrent_document_upload or ensure documents
        exist in the system before running this test in isolation.
        """
        runner = _build_runner(rag_config)
        runner.document_filenames = [fname for _, fname, _ in batch_pdf_documents]
        runner.celery_monitor = celery_monitor

        test_start = datetime.now(timezone.utc)

        async def _trigger():
            import aiohttp

            async with aiohttp.ClientSession() as session:
                await runner.trigger_embedding_pipeline(session)

        _run_async(_trigger())

        # Wait briefly for tasks to be queued before polling
        import time
        time.sleep(10)

        # Count relevant tasks that already completed (from previous
        # tests or auto-triggered embedding). Inflate NUM_DOCUMENTS so
        # the monitor waits for baseline + expected NEW tasks.
        baseline = _count_relevant_completed_tasks(celery_monitor, test_start)
        runner.config.NUM_DOCUMENTS = rag_config.num_documents + baseline

        runner.monitor_celery_tasks(test_start)

        # Print report
        empty_upload = UploadStats()
        with capsys.disabled():
            print(self.build_report_lines(empty_upload, runner.embedding_stats))

        # Assertions
        self.assert_embedding_tasks_completed(
            runner.embedding_stats,
            min_success=int(rag_config.num_documents * 0.95),
            allow_failures=False,
        )

    # ------------------------------------------------------------------
    # Test 3 – Full end-to-end flow
    # ------------------------------------------------------------------

    @pytest.mark.slow
    def test_full_upload_and_embed_flow(
        self,
        rag_config: RagTestConfig,
        batch_pdf_documents: List[Tuple[int, str, bytes]],
        celery_monitor,
        capsys,
    ):
        """Run the complete upload → embed → verify flow end-to-end.

        This is the primary integration test that mirrors the original
        stress_test_doc_upload.py script but executed within pytest so
        results are captured as pass/fail.

        Phases:
        1. Upload N PDFs concurrently
        2. Trigger embedding pipeline
        3. Monitor Celery tasks until completion or timeout
        4. Assert both phases met their success-rate thresholds
        """
        runner = _build_runner(rag_config)
        runner.document_filenames = [fname for _, fname, _ in batch_pdf_documents]
        runner.celery_monitor = celery_monitor

        test_start = datetime.now(timezone.utc)

        # Phase 1 + Phase 2 (upload then trigger embed)
        async def _upload_and_embed():
            import aiohttp

            runner.upload_stats.start_time = __import__("time").time()
            async with aiohttp.ClientSession() as session:
                for i in range(0, len(batch_pdf_documents), rag_config.concurrent_uploads):
                    batch = batch_pdf_documents[i: i + rag_config.concurrent_uploads]
                    await runner.upload_batch(session, batch)

            runner.upload_stats.end_time = __import__("time").time()

            if runner.upload_stats.successful_uploads > 0:
                async with aiohttp.ClientSession() as session:
                    await runner.trigger_embedding_pipeline(session)

        _run_async(_upload_and_embed())

        # Phase 3 – monitor Celery tasks
        if runner.upload_stats.successful_uploads > 0:
            import time
            time.sleep(10)

            # Count relevant tasks that already completed (from auto-triggered
            # embedding on upload). Inflate NUM_DOCUMENTS so the monitor waits
            # for baseline + expected NEW tasks.
            baseline = _count_relevant_completed_tasks(celery_monitor, test_start)
            runner.config.NUM_DOCUMENTS = rag_config.num_documents + baseline

            runner.monitor_celery_tasks(test_start)
        else:
            pytest.skip(
                "No successful uploads – skipping Celery monitoring phase. "
                "Ensure the RAG API is reachable at: "
                f"{rag_config.api_base_url}"
            )

        # Print report
        with capsys.disabled():
            print(
                self.build_report_lines(runner.upload_stats, runner.embedding_stats)
            )

        # Assertions
        self.assert_full_flow_passed(
            upload_stats=runner.upload_stats,
            embedding_stats=runner.embedding_stats,
            total_docs=rag_config.num_documents,
            min_upload_rate=95.0,
            min_embed_rate=95.0,
        )
