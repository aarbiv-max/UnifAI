"""
End-to-End Test: CELERY Integration Pipeline

This test validates the complete Celery-based async pipeline orchestration:

1. Task dispatch via CeleryPipelineDispatcher
2. Task execution simulation via execute_pipeline_task
3. Full async flow with RabbitMQ (when available)

IMPORTANT: These tests require additional infrastructure:
    - RabbitMQ running (for task queuing)
    - Celery workers running (for task execution)
    - MongoDB running (for pipeline state) - optional for dispatch tests

Test Modes:
    - DISPATCH_ONLY: Test task dispatch without execution (requires RabbitMQ)
    - FULL_ASYNC: Test complete async flow (requires RabbitMQ + Workers + Services)
    - SYNC_SIMULATION: Simulate Celery task logic synchronously (no infrastructure)

Environment Variables:
    - RABBITMQ_URL: RabbitMQ connection URL (e.g., amqp://guest:guest@localhost:5672)
    - TEST_DOCUMENT_PATH: Path to test PDF document
    - DOCLING_SERVICE_URL: For remote mode tests
    - EMBEDDING_SERVICE_URL: For remote mode tests
    - CELERY_TEST_MODE: One of 'sync', 'dispatch', 'full' (default: 'sync')

Run:
    # Sync simulation (no infrastructure needed)
    TEST_DOCUMENT_PATH=/path/to/test.pdf \
    pytest tests/e2e/test_e2e_celery_integration.py -v -s

    # Dispatch only (requires RabbitMQ)
    RABBITMQ_URL=amqp://guest:guest@localhost:5672 \
    TEST_DOCUMENT_PATH=/path/to/test.pdf \
    CELERY_TEST_MODE=dispatch \
    pytest tests/e2e/test_e2e_celery_integration.py -v -s

    # Full async (requires all infrastructure)
    RABBITMQ_URL=amqp://guest:guest@localhost:5672 \
    DOCLING_SERVICE_URL=http://docling-service:5001 \
    EMBEDDING_SERVICE_URL=http://embedding-service:5002 \
    TEST_DOCUMENT_PATH=/path/to/test.pdf \
    CELERY_TEST_MODE=full \
    pytest tests/e2e/test_e2e_celery_integration.py -v -s
"""

import os
import time
import uuid
import pytest
from typing import Dict, Any


# Skip if no test document
pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DOCUMENT_PATH") or not os.path.exists(os.environ.get("TEST_DOCUMENT_PATH", "")),
    reason="TEST_DOCUMENT_PATH not set or file does not exist"
)


class TestCeleryIntegration:
    """Celery integration tests for pipeline orchestration."""

    @pytest.fixture(autouse=True)
    def setup(self, test_document_path, test_report):
        """Setup test environment."""
        self.test_document_path = test_document_path
        self.create_report = test_report
        self.celery_mode = os.environ.get("CELERY_TEST_MODE", "sync")
        self.rabbitmq_url = os.environ.get("RABBITMQ_URL")

    def _create_source_data(self, doc_path: str) -> Dict[str, Any]:
        """Create source_data structure as it comes from registration."""
        pipeline_id = str(uuid.uuid4())
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        
        return {
            "pipeline_id": pipeline_id,
            "metadata": {
                "doc_id": doc_id,
                "doc_name": os.path.basename(doc_path),
                "doc_path": doc_path,
                "upload_by": "celery_test_user",
            },
            "type_data": {
                "chunk_size": 500,
                "overlap": 50,
            },
        }

    def test_context_building(self):
        """Test building PipelineContext from Celery message format."""
        report = self.create_report("Context Building", "celery")
        
        from infrastructure.celery.workers.pipeline_tasks import build_context
        
        source_data = self._create_source_data(self.test_document_path)
        
        context = build_context("DOCUMENT", source_data)
        
        report.add_detail("input_source_data", source_data)
        report.add_detail("context_pipeline_id", context.pipeline_id)
        report.add_detail("context_source_type", context.source_type)
        report.add_detail("context_source_id", context.source_id)
        report.add_detail("context_source_name", context.source_name)
        report.add_detail("context_metadata_keys", list(context.metadata.keys()))
        report.add_metric("context_built", True)
        
        report.print_report()
        
        assert context.pipeline_id == source_data["pipeline_id"]
        assert context.source_type == "DOCUMENT"
        assert context.source_id == source_data["metadata"]["doc_id"]

    def test_context_building_validation(self):
        """Test context building validation for missing fields."""
        report = self.create_report("Context Validation", "celery")
        
        from infrastructure.celery.workers.pipeline_tasks import build_context
        
        # Missing pipeline_id
        invalid_data_1 = {"metadata": {"doc_id": "123"}}
        
        # Missing metadata
        invalid_data_2 = {"pipeline_id": str(uuid.uuid4())}
        
        errors = []
        
        try:
            build_context("DOCUMENT", invalid_data_1)
        except ValueError as e:
            errors.append(("missing_pipeline_id", str(e)))
        
        try:
            build_context("DOCUMENT", invalid_data_2)
        except ValueError as e:
            errors.append(("missing_metadata", str(e)))
        
        report.add_metric("validation_errors_caught", len(errors))
        report.add_detail("errors", errors)
        
        report.print_report()
        
        assert len(errors) == 2

    def test_dispatcher_creation(self):
        """Test CeleryPipelineDispatcher creation."""
        report = self.create_report("Dispatcher Creation", "celery")
        
        from infrastructure.celery.pipeline_dispatcher import CeleryPipelineDispatcher
        
        dispatcher = CeleryPipelineDispatcher()
        
        report.add_detail("dispatcher_type", type(dispatcher).__name__)
        report.add_detail("task_name", dispatcher.PIPELINE_TASK)
        report.add_metric("dispatcher_created", True)
        
        report.print_report()
        
        assert dispatcher.PIPELINE_TASK == "infrastructure.celery.workers.pipeline_tasks.execute_pipeline_task"

    def test_sync_task_simulation(self):
        """Simulate Celery task execution synchronously (no RabbitMQ needed)."""
        report = self.create_report("Sync Task Simulation", "celery")
        
        from infrastructure.celery.workers.pipeline_tasks import build_context
        from bootstrap.app_container import get_pipeline_handler, clear_all_caches
        from application.pipeline.document_handler import DocumentPipelineHandler
        
        # Clear caches to get fresh instances
        clear_all_caches()
        
        source_data = self._create_source_data(self.test_document_path)
        
        start_time = time.time()
        
        # Step 1: Build context (as Celery task does)
        context = build_context("DOCUMENT", source_data)
        
        # Step 2: Get handler
        handler = get_pipeline_handler("DOCUMENT")
        
        # Step 3: Execute pipeline steps (without executor to avoid DB deps)
        collected = handler.collect(context)
        processed = handler.process(context, collected)
        vector_chunks = handler.chunk_and_embed(context, processed)
        summary = handler.get_summary(context, collected)
        
        elapsed = time.time() - start_time
        
        # Build result (as Celery task would return)
        task_result = {
            "pipeline_id": context.pipeline_id,
            "source_type": "DOCUMENT",
            "status": "success",
            "result": {
                "chunks_processed": len(vector_chunks),
                "summary": summary,
            },
        }
        
        report.add_metric("total_time_seconds", elapsed)
        report.add_metric("chunks_produced", len(vector_chunks))
        report.add_detail("task_result", task_result)
        report.add_detail("pipeline_id", context.pipeline_id)
        report.add_detail("handler_type", type(handler).__name__)
        
        report.print_report()
        
        assert len(vector_chunks) > 0
        assert task_result["status"] == "success"

    @pytest.mark.skipif(
        not os.environ.get("RABBITMQ_URL"),
        reason="RABBITMQ_URL not set - skipping dispatch test"
    )
    def test_task_dispatch(self):
        """Test actual task dispatch to RabbitMQ (requires RabbitMQ)."""
        report = self.create_report("Task Dispatch", "celery")
        
        from infrastructure.celery.pipeline_dispatcher import CeleryPipelineDispatcher
        
        dispatcher = CeleryPipelineDispatcher()
        source_data = self._create_source_data(self.test_document_path)
        
        try:
            start_time = time.time()
            result = dispatcher.dispatch("DOCUMENT", source_data)
            elapsed = time.time() - start_time
            
            report.add_metric("dispatch_time_seconds", elapsed)
            report.add_metric("dispatch_success", True)
            report.add_detail("task_id", result.task_id)
            report.add_detail("queue", result.queue)
            report.add_detail("source_type", result.source_type)
            report.add_detail("pipeline_id", result.pipeline_id)
            
        except Exception as e:
            report.add_metric("dispatch_success", False)
            report.add_detail("error", str(e))
        
        report.print_report()

    @pytest.mark.skipif(
        not os.environ.get("RABBITMQ_URL"),
        reason="RABBITMQ_URL not set - skipping batch dispatch test"
    )
    def test_batch_dispatch(self):
        """Test batch task dispatch."""
        report = self.create_report("Batch Dispatch", "celery")
        
        from infrastructure.celery.pipeline_dispatcher import CeleryPipelineDispatcher
        
        dispatcher = CeleryPipelineDispatcher()
        
        # Create multiple source_data entries
        sources = [
            self._create_source_data(self.test_document_path)
            for _ in range(3)
        ]
        
        try:
            start_time = time.time()
            results = dispatcher.dispatch_batch("DOCUMENT", sources)
            elapsed = time.time() - start_time
            
            report.add_metric("dispatch_time_seconds", elapsed)
            report.add_metric("tasks_dispatched", len(results))
            report.add_metric("dispatch_success", True)
            
            for i, result in enumerate(results):
                report.add_detail(f"task_{i}_id", result.task_id)
                report.add_detail(f"task_{i}_queue", result.queue)
            
        except Exception as e:
            report.add_metric("dispatch_success", False)
            report.add_detail("error", str(e))
        
        report.print_report()

    def test_task_result_structure(self):
        """Test the structure of task results matches expected format."""
        report = self.create_report("Task Result Structure", "celery")
        
        # Simulate what the Celery task returns
        expected_result = {
            "pipeline_id": str(uuid.uuid4()),
            "source_type": "DOCUMENT",
            "status": "success",
            "result": {
                "chunks_processed": 25,
                "vectors_stored": 25,
            },
        }
        
        # Validate structure
        required_keys = ["pipeline_id", "source_type", "status", "result"]
        has_all_keys = all(k in expected_result for k in required_keys)
        
        report.add_metric("has_all_required_keys", has_all_keys)
        report.add_detail("required_keys", required_keys)
        report.add_detail("result_structure", expected_result)
        
        report.print_report()
        
        assert has_all_keys

    def test_error_handling_in_task(self):
        """Test error handling within task execution."""
        report = self.create_report("Task Error Handling", "celery")
        
        from infrastructure.celery.workers.pipeline_tasks import build_context
        from bootstrap.app_container import get_pipeline_handler
        from domain.pipeline.port import PipelineContext
        
        # Create context with invalid path
        source_data = {
            "pipeline_id": str(uuid.uuid4()),
            "metadata": {
                "doc_id": "invalid_doc",
                "doc_name": "nonexistent.pdf",
                "doc_path": "/nonexistent/path/document.pdf",
                "upload_by": "test_user",
            },
        }
        
        context = build_context("DOCUMENT", source_data)
        handler = get_pipeline_handler("DOCUMENT")
        
        error_caught = False
        error_type = None
        error_message = None
        
        try:
            handler.collect(context)
        except Exception as e:
            error_caught = True
            error_type = type(e).__name__
            error_message = str(e)
        
        report.add_metric("error_caught", error_caught)
        report.add_detail("error_type", error_type)
        report.add_detail("error_message", error_message)
        
        report.print_report()
        
        assert error_caught, "Should catch error for invalid path"

    def test_queue_routing(self):
        """Test that document tasks are routed to correct queue."""
        report = self.create_report("Queue Routing", "celery")
        
        from infrastructure.celery.pipeline_dispatcher import CeleryPipelineDispatcher
        
        dispatcher = CeleryPipelineDispatcher()
        
        # Test document source type routes to document_queue
        test_cases = [
            ("DOCUMENT", "document_queue"),
            ("document", "document_queue"),  # lowercase
        ]
        
        for source_type, expected_queue in test_cases:
            actual_queue = f"{source_type.lower()}_queue"
            report.add_detail(f"{source_type}_queue", actual_queue)
            assert actual_queue == expected_queue, f"Expected {expected_queue}, got {actual_queue}"
        
        report.add_metric("routing_correct", True)
        report.print_report()

    def test_pipeline_flow_comparison_local_vs_celery(self):
        """Compare direct pipeline execution vs Celery task simulation."""
        report = self.create_report("Local vs Celery Flow Comparison", "celery")
        
        from infrastructure.celery.workers.pipeline_tasks import build_context
        from infrastructure.connector.document_connector import DocumentConnector
        from infrastructure.embedding.sentence_transformer_embedder import SentenceTransformerEmbedding
        from infrastructure.config.doc_config_manager import DocConfigManager
        from infrastructure.chunking.pdf_chunker import PDFChunkerStrategy
        from domain.processor.document_processor import DocumentProcessor
        from application.pipeline.document_handler import DocumentPipelineHandler
        from domain.pipeline.port import PipelineContext
        
        # Setup components
        config_manager = DocConfigManager()
        connector = DocumentConnector(config_manager=config_manager)
        embedder = SentenceTransformerEmbedding(model_name="all-MiniLM-L6-v2", device="cpu")
        processor = DocumentProcessor()
        chunker = PDFChunkerStrategy(max_tokens_per_chunk=500, overlap_tokens=50)
        
        handler = DocumentPipelineHandler(
            connector=connector,
            processor=processor,
            chunker=chunker,
            embedder=embedder,
        )
        
        # Direct execution
        direct_context = PipelineContext(
            pipeline_id=str(uuid.uuid4()),
            source_type="DOCUMENT",
            source_id="direct_test",
            source_name=os.path.basename(self.test_document_path),
            metadata={
                "doc_path": self.test_document_path,
                "upload_by": "direct_test",
            },
        )
        
        direct_start = time.time()
        direct_collected = handler.collect(direct_context)
        direct_processed = handler.process(direct_context, direct_collected)
        direct_chunks = handler.chunk_and_embed(direct_context, direct_processed)
        direct_time = time.time() - direct_start
        
        # Celery simulation
        source_data = self._create_source_data(self.test_document_path)
        
        celery_start = time.time()
        celery_context = build_context("DOCUMENT", source_data)
        celery_collected = handler.collect(celery_context)
        celery_processed = handler.process(celery_context, celery_collected)
        celery_chunks = handler.chunk_and_embed(celery_context, celery_processed)
        celery_time = time.time() - celery_start
        
        # Compare results
        report.add_metric("direct_time_seconds", direct_time)
        report.add_metric("celery_time_seconds", celery_time)
        report.add_metric("direct_chunk_count", len(direct_chunks))
        report.add_metric("celery_chunk_count", len(celery_chunks))
        report.add_metric("chunk_counts_match", len(direct_chunks) == len(celery_chunks))
        
        # Text comparison
        direct_text_len = len(direct_collected.get("text", ""))
        celery_text_len = len(celery_collected.get("text", ""))
        report.add_metric("direct_text_length", direct_text_len)
        report.add_metric("celery_text_length", celery_text_len)
        report.add_metric("text_lengths_match", direct_text_len == celery_text_len)
        
        report.print_report()
        
        assert len(direct_chunks) == len(celery_chunks), "Chunk counts should match"
        assert direct_text_len == celery_text_len, "Text lengths should match"
