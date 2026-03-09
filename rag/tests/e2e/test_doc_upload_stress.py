"""
End-to-End Stress Test for Document Upload and Embedding Pipeline.

Validates the RAG system's ability to handle concurrent document uploads
and embedding pipeline execution under load.

Mirrors the standalone stress_test_doc_upload.py script by calling
runner.run() directly — same upload, embed, monitor, and report flow.

Run with:
    pytest tests/e2e/test_doc_upload_stress.py -v -s
    pytest tests/e2e/test_doc_upload_stress.py -v -s \\
        --api-base-url http://myserver/api \\
        --num-docs 50 \\
        --concurrent-uploads 5
"""

import asyncio
import pytest

from tests.base.base_e2e_test import BaseE2ETest
from tests.fixtures.common.api_fixtures import RagTestConfig
from tests.docs.stress_test_doc_upload import StressTestRunner


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


# =============================================================================
# TEST CLASS
# =============================================================================

@pytest.mark.e2e
@pytest.mark.stress
@pytest.mark.document
@pytest.mark.rag
class TestDocumentUploadStress(BaseE2ETest):
    """End-to-end stress test for RAG document upload and embedding pipeline.

    Calls runner.run() directly — the exact same code path as the
    standalone stress_test_doc_upload.py script.
    """

    @pytest.mark.slow
    def test_full_upload_and_embed_flow(
        self,
        rag_config: RagTestConfig,
        capsys,
    ):
        """Run the complete upload → embed → verify flow end-to-end.

        Calls runner.run() directly — the exact same code path as the
        standalone stress_test_doc_upload.py script:
        1. Upload N PDFs concurrently
        2. Trigger embedding pipeline
        3. Wait 10 s for tasks to be queued
        4. Monitor Celery tasks until completion or timeout
        5. Print final report
        """
        runner = _build_runner(rag_config)

        _run_async(runner.run())

        with capsys.disabled():
            print(
                self.build_report_lines(runner.upload_stats, runner.embedding_stats)
            )

        self.assert_full_flow_passed(
            upload_stats=runner.upload_stats,
            embedding_stats=runner.embedding_stats,
            total_docs=rag_config.num_documents,
            min_upload_rate=95.0,
            min_embed_rate=95.0,
        )
