"""Unit tests for PipelineService."""
from datetime import datetime
from unittest.mock import MagicMock, create_autospec

import pytest

from core.pipeline.domain.model import PipelineRecord, PipelineStatus, PipelineStats
from core.pipeline.domain.repository import PipelineRepository
from core.pipeline.service import PipelineService


# ═══════════════════════════════════════════════════════════════════════════════
# Module-level fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_repo():
    return create_autospec(PipelineRepository, instance=True)


@pytest.fixture
def service(mock_repo):
    return PipelineService(pipeline_repo=mock_repo)


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
@pytest.mark.document
@pytest.mark.pipeline
class TestPipelineService:

    # --- register ---

    def test_register_creates_new_record(self, service, mock_repo):
        mock_repo.find_by_id.return_value = None

        record = service.register("p1", "DOCUMENT")

        assert record.pipeline_id == "p1"
        assert record.source_type == "DOCUMENT"
        assert record.status == PipelineStatus.PENDING
        mock_repo.save.assert_called_once()

    def test_register_existing_updates_timestamp(self, service, mock_repo):
        old_time = datetime(2025, 1, 1)
        existing = PipelineRecord(
            pipeline_id="p1",
            source_type="DOCUMENT",
            status=PipelineStatus.DONE,
            created_at=old_time,
            last_updated=old_time,
        )
        mock_repo.find_by_id.return_value = existing

        record = service.register("p1", "DOCUMENT")

        assert record.last_updated > old_time
        mock_repo.save.assert_called_once_with(existing)

    # --- update_status ---

    def test_update_status_success(self, service, mock_repo):
        record = PipelineRecord(
            pipeline_id="p1",
            source_type="DOCUMENT",
            status=PipelineStatus.PENDING,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
        )
        mock_repo.find_by_id.return_value = record

        result = service.update_status("p1", PipelineStatus.COLLECTING)

        assert result is True
        assert record.status == PipelineStatus.COLLECTING
        mock_repo.save.assert_called_once()

    def test_update_status_calculates_processing_time_on_done(self, service, mock_repo):
        created = datetime(2025, 1, 1, 0, 0, 0)
        record = PipelineRecord(
            pipeline_id="p1",
            source_type="DOCUMENT",
            status=PipelineStatus.STORING,
            created_at=created,
            last_updated=created,
            stats=PipelineStats(),
        )
        mock_repo.find_by_id.return_value = record

        service.update_status("p1", PipelineStatus.DONE)

        assert record.stats.processing_time > 0

    def test_update_status_no_processing_time_on_other_statuses(self, service, mock_repo):
        record = PipelineRecord(
            pipeline_id="p1",
            source_type="DOCUMENT",
            status=PipelineStatus.PENDING,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            stats=PipelineStats(),
        )
        mock_repo.find_by_id.return_value = record

        service.update_status("p1", PipelineStatus.COLLECTING)

        assert record.stats.processing_time == 0.0

    def test_update_status_from_string(self, service, mock_repo):
        record = PipelineRecord(
            pipeline_id="p1",
            source_type="DOCUMENT",
            status=PipelineStatus.PENDING,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
        )
        mock_repo.find_by_id.return_value = record

        service.update_status("p1", "PROCESSING")

        assert record.status == PipelineStatus.PROCESSING

    def test_update_status_nonexistent_returns_false(self, service, mock_repo):
        mock_repo.find_by_id.return_value = None

        result = service.update_status("missing", PipelineStatus.DONE)

        assert result is False
        mock_repo.save.assert_not_called()

    # --- get / delete ---

    def test_get_delegates_to_repo(self, service, mock_repo):
        mock_repo.find_by_id.return_value = MagicMock()
        service.get("p1")
        mock_repo.find_by_id.assert_called_once_with("p1")

    def test_delete_delegates_to_repo(self, service, mock_repo):
        mock_repo.delete.return_value = 1
        result = service.delete("p1")
        assert result == 1
        mock_repo.delete.assert_called_once_with("p1")
