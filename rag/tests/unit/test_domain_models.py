"""Unit tests for domain models: PipelineStats, PipelineRecord, DataSource, PipelineStartResult."""
from datetime import datetime

import pytest

from core.pipeline.domain.model import PipelineStats, PipelineRecord, PipelineStatus
from core.data_sources.domain.model import DataSource
from core.pipeline.dispatch_service import PipelineStartResult


# ═══════════════════════════════════════════════════════════════════════════════
# PipelineStats
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.document
class TestPipelineStats:

    def test_from_dict_with_all_fields(self):
        data = {
            "documents_retrieved": 10,
            "chunks_generated": 50,
            "embeddings_created": 50,
            "api_calls": 3,
            "processing_time": 12.5,
        }
        stats = PipelineStats.from_dict(data)
        assert stats.documents_retrieved == 10
        assert stats.chunks_generated == 50
        assert stats.embeddings_created == 50
        assert stats.api_calls == 3
        assert stats.processing_time == 12.5

    def test_from_dict_with_missing_fields_defaults_to_zero(self):
        stats = PipelineStats.from_dict({"documents_retrieved": 7})
        assert stats.documents_retrieved == 7
        assert stats.chunks_generated == 0
        assert stats.embeddings_created == 0
        assert stats.api_calls == 0
        assert stats.processing_time == 0.0

    def test_to_dict_round_trip(self):
        original = PipelineStats(
            documents_retrieved=5,
            chunks_generated=20,
            embeddings_created=20,
            api_calls=2,
            processing_time=8.0,
        )
        restored = PipelineStats.from_dict(original.to_dict())
        assert restored == original


# ═══════════════════════════════════════════════════════════════════════════════
# PipelineRecord
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.document
class TestPipelineRecord:

    def test_from_dict_valid_status(self):
        data = {
            "pipeline_id": "p1",
            "source_type": "DOCUMENT",
            "status": "DONE",
            "created_at": datetime(2025, 1, 1),
            "last_updated": datetime(2025, 1, 2),
            "stats": {},
        }
        record = PipelineRecord.from_dict(data)
        assert record.status == PipelineStatus.DONE

    def test_from_dict_invalid_status_defaults_to_pending(self):
        data = {
            "pipeline_id": "p2",
            "source_type": "DOCUMENT",
            "status": "BOGUS",
        }
        record = PipelineRecord.from_dict(data)
        assert record.status == PipelineStatus.PENDING

    def test_to_dict_serializes_status_as_string(self):
        record = PipelineRecord(
            pipeline_id="p3",
            source_type="DOCUMENT",
            status=PipelineStatus.COLLECTING,
            created_at=datetime(2025, 1, 1),
            last_updated=datetime(2025, 1, 1),
        )
        d = record.to_dict()
        assert d["status"] == "COLLECTING"
        assert isinstance(d["status"], str)


# ═══════════════════════════════════════════════════════════════════════════════
# DataSource
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.document
class TestDataSource:

    def test_from_dict_round_trip(self):
        now = datetime(2025, 6, 1)
        data = {
            "source_id": "s1",
            "source_name": "report.pdf",
            "source_type": "DOCUMENT",
            "pipeline_id": "p1",
            "upload_by": "alice",
            "created_at": now,
            "last_sync_at": now,
            "tags": ["finance"],
            "type_data": {"page_count": 10},
        }
        source = DataSource.from_dict(data)
        restored = DataSource.from_dict(source.to_dict())
        assert restored.source_id == "s1"
        assert restored.source_name == "report.pdf"
        assert restored.tags == ["finance"]
        assert restored.type_data == {"page_count": 10}

    def test_defaults(self):
        source = DataSource.from_dict({
            "source_id": "s2",
            "source_name": "doc.pdf",
            "source_type": "DOCUMENT",
            "pipeline_id": "p2",
            "upload_by": "bob",
            "created_at": datetime.now(),
        })
        assert source.tags == []
        assert source.type_data == {}
        assert source.last_sync_at is None


# ═══════════════════════════════════════════════════════════════════════════════
# PipelineStartResult
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.document
class TestPipelineStartResult:

    def test_to_dict_with_dispatched_tasks(self):
        result = PipelineStartResult(
            registration_completed=True,
            registered_count=3,
            tasks_dispatched=3,
            registration_response={"status": "ok"},
            task_results=[{"task_id": "t1"}],
        )
        d = result.to_dict()
        assert d["pipeline_execution"]["status"] == "pipeline_workflow_started"
        assert d["pipeline_execution"]["pipeline_worker_tasks_submitted"] == 3

    def test_to_dict_with_no_sources(self):
        result = PipelineStartResult(
            registration_completed=True,
            registered_count=0,
            tasks_dispatched=0,
            registration_response={"status": "ok"},
        )
        d = result.to_dict()
        assert d["pipeline_execution"]["status"] == "no_registered_sources"
        assert "No sources registered" in d["pipeline_execution"]["message"]
