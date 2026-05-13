"""
Unit tests for scripts/seed_templates.py.

Tests the load_seed_files and seed_templates logic with mocked MongoDB and
a temporary seed directory, without touching the real database.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import sys
import importlib

# ---------------------------------------------------------------------------
# Helpers: import script under test
# ---------------------------------------------------------------------------

SEED_SCRIPT = Path(__file__).parents[4] / "scripts" / "seed_templates.py"


def _load_script():
    """Dynamically import seed_templates without executing __main__."""
    spec = importlib.util.spec_from_file_location("seed_templates", SEED_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seed_dir(tmp_path):
    """Temporary directory acting as the seeds folder."""
    return tmp_path / "template-seeds"


@pytest.fixture
def valid_seed(seed_dir):
    """Write one valid seed JSON file and return its data."""
    seed_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "template_id": "test-template-001",
        "draft": {"name": "Test Template"},
        "placeholders": {"categories": []},
        "metadata": {"author": "test", "tags": [], "version": "1.0.0"},
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (seed_dir / "test-template-001.json").write_text(json.dumps(data))
    return data


@pytest.fixture
def mock_collection():
    """A mock pymongo collection."""
    col = MagicMock()
    col.find_one.return_value = None  # no existing doc by default
    return col


@pytest.fixture
def mock_db(mock_collection):
    """A mock pymongo database."""
    db = MagicMock()
    db.__getitem__.return_value = mock_collection
    return db


# ---------------------------------------------------------------------------
# Tests: load_seed_files
# ---------------------------------------------------------------------------

class TestLoadSeedFiles:
    """Tests for the load_seed_files helper."""

    def test_loads_valid_json(self, seed_dir, valid_seed, monkeypatch):
        mod = _load_script()
        monkeypatch.setattr(mod, "SEEDS_DIR", seed_dir)
        results = mod.load_seed_files()
        assert len(results) == 1
        filename, data = results[0]
        assert filename == "test-template-001.json"
        assert data["template_id"] == "test-template-001"

    def test_skips_file_without_template_id(self, seed_dir, monkeypatch):
        seed_dir.mkdir(parents=True, exist_ok=True)
        (seed_dir / "bad.json").write_text(json.dumps({"no_id": True}))

        mod = _load_script()
        monkeypatch.setattr(mod, "SEEDS_DIR", seed_dir)
        results = mod.load_seed_files()
        assert results == []

    def test_skips_invalid_json(self, seed_dir, monkeypatch):
        seed_dir.mkdir(parents=True, exist_ok=True)
        (seed_dir / "broken.json").write_text("NOT VALID JSON {{")

        mod = _load_script()
        monkeypatch.setattr(mod, "SEEDS_DIR", seed_dir)
        results = mod.load_seed_files()
        assert results == []

    def test_empty_directory_returns_empty(self, seed_dir, monkeypatch):
        seed_dir.mkdir(parents=True, exist_ok=True)
        mod = _load_script()
        monkeypatch.setattr(mod, "SEEDS_DIR", seed_dir)
        results = mod.load_seed_files()
        assert results == []

    def test_loads_multiple_files_sorted(self, seed_dir, monkeypatch):
        seed_dir.mkdir(parents=True, exist_ok=True)
        for i in ["b", "a", "c"]:
            (seed_dir / f"{i}.json").write_text(json.dumps({"template_id": i}))

        mod = _load_script()
        monkeypatch.setattr(mod, "SEEDS_DIR", seed_dir)
        results = mod.load_seed_files()
        filenames = [fname for fname, _ in results]
        assert filenames == sorted(filenames), "Files must be returned in sorted order"


# ---------------------------------------------------------------------------
# Tests: seed_templates (upsert logic)
# ---------------------------------------------------------------------------

class TestSeedTemplates:
    """Tests for the seed_templates upsert logic."""

    def test_dry_run_does_not_call_replace_one(
        self, seed_dir, valid_seed, monkeypatch, mock_db, mock_collection
    ):
        mod = _load_script()
        monkeypatch.setattr(mod, "SEEDS_DIR", seed_dir)
        mod.seed_templates(mock_db, dry_run=True)
        mock_collection.replace_one.assert_not_called()

    def test_apply_inserts_new_document(
        self, seed_dir, valid_seed, monkeypatch, mock_db, mock_collection
    ):
        mock_collection.find_one.return_value = None  # no existing doc
        mod = _load_script()
        monkeypatch.setattr(mod, "SEEDS_DIR", seed_dir)
        stats = mod.seed_templates(mock_db, dry_run=False)
        mock_collection.replace_one.assert_called_once()
        assert stats["inserted"] == 1
        assert stats["updated"] == 0

    def test_apply_updates_existing_document(
        self, seed_dir, valid_seed, monkeypatch, mock_db, mock_collection
    ):
        # Simulate existing doc
        mock_collection.find_one.return_value = {"template_id": "test-template-001"}
        mod = _load_script()
        monkeypatch.setattr(mod, "SEEDS_DIR", seed_dir)
        stats = mod.seed_templates(mock_db, dry_run=False)
        mock_collection.replace_one.assert_called_once()
        assert stats["updated"] == 1
        assert stats["inserted"] == 0

    def test_apply_stamps_updated_at(
        self, seed_dir, valid_seed, monkeypatch, mock_db, mock_collection
    ):
        mock_collection.find_one.return_value = None
        mod = _load_script()
        monkeypatch.setattr(mod, "SEEDS_DIR", seed_dir)
        mod.seed_templates(mock_db, dry_run=False)

        call_args = mock_collection.replace_one.call_args
        upserted_doc = call_args[0][1]  # second positional arg (replacement)
        assert "updated_at" in upserted_doc, "updated_at must be stamped on upsert"

    def test_apply_upsert_flag_is_true(
        self, seed_dir, valid_seed, monkeypatch, mock_db, mock_collection
    ):
        mock_collection.find_one.return_value = None
        mod = _load_script()
        monkeypatch.setattr(mod, "SEEDS_DIR", seed_dir)
        mod.seed_templates(mock_db, dry_run=False)

        call_kwargs = mock_collection.replace_one.call_args[1]
        assert call_kwargs.get("upsert") is True, "replace_one must use upsert=True"

    def test_error_during_upsert_is_captured(
        self, seed_dir, valid_seed, monkeypatch, mock_db, mock_collection
    ):
        mock_collection.find_one.return_value = None
        mock_collection.replace_one.side_effect = Exception("DB connection lost")
        mod = _load_script()
        monkeypatch.setattr(mod, "SEEDS_DIR", seed_dir)
        stats = mod.seed_templates(mock_db, dry_run=False)
        assert len(stats["errors"]) == 1
        assert "test-template-001" in stats["errors"][0]

    def test_dry_run_counts_inserted(
        self, seed_dir, valid_seed, monkeypatch, mock_db, mock_collection
    ):
        mock_collection.find_one.return_value = None
        mod = _load_script()
        monkeypatch.setattr(mod, "SEEDS_DIR", seed_dir)
        stats = mod.seed_templates(mock_db, dry_run=True)
        assert stats["inserted"] == 1
        assert stats["errors"] == []

    def test_empty_seed_dir_returns_zero_counts(
        self, seed_dir, monkeypatch, mock_db, mock_collection
    ):
        seed_dir.mkdir(parents=True, exist_ok=True)
        mod = _load_script()
        monkeypatch.setattr(mod, "SEEDS_DIR", seed_dir)
        stats = mod.seed_templates(mock_db, dry_run=False)
        assert stats["inserted"] == 0
        assert stats["updated"] == 0
        assert stats["errors"] == []
        mock_collection.replace_one.assert_not_called()
