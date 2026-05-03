"""Tests for devtool.services.patcher."""

from __future__ import annotations

from pathlib import Path

import pytest

from devtool.domain.models import (
    PatchSpec,
    Service,
    ServiceType,
    VenvConfig,
    VenvStrategy,
)
from devtool.services.patcher import apply_patches


def _make_service(patches: list[PatchSpec]) -> Service:
    return Service(
        name="test-svc",
        directory=Path("svc"),
        type=ServiceType.PYTHON,
        launch="echo ok",
        venv=VenvConfig(strategy=VenvStrategy.NONE),
        patches=patches,
    )


class TestApplyPatches:
    def test_applies_patch(self, tmp_path: Path) -> None:
        target = tmp_path / "svc" / "app.py"
        target.parent.mkdir(parents=True)
        target.write_text('app.run(host="localhost")')

        svc = _make_service([
            PatchSpec(
                file=Path("svc/app.py"),
                find='host="localhost"',
                replace='host="0.0.0.0"',
            ),
        ])
        modified = apply_patches(svc, tmp_path)

        assert modified == ["svc/app.py"]
        assert 'host="0.0.0.0"' in target.read_text()

    def test_already_patched_skips(self, tmp_path: Path) -> None:
        target = tmp_path / "svc" / "app.py"
        target.parent.mkdir(parents=True)
        target.write_text('app.run(host="0.0.0.0")')

        svc = _make_service([
            PatchSpec(
                file=Path("svc/app.py"),
                find='host="localhost"',
                replace='host="0.0.0.0"',
            ),
        ])
        modified = apply_patches(svc, tmp_path)

        assert modified == []

    def test_missing_file_skips(self, tmp_path: Path, capsys) -> None:
        svc = _make_service([
            PatchSpec(
                file=Path("svc/missing.py"),
                find="a",
                replace="b",
            ),
        ])
        modified = apply_patches(svc, tmp_path)

        assert modified == []
        assert "not found" in capsys.readouterr().out

    def test_stale_pattern_warns(self, tmp_path: Path, capsys) -> None:
        target = tmp_path / "svc" / "app.py"
        target.parent.mkdir(parents=True)
        target.write_text("completely different content")

        svc = _make_service([
            PatchSpec(
                file=Path("svc/app.py"),
                find="nonexistent_pattern",
                replace="replacement",
            ),
        ])
        modified = apply_patches(svc, tmp_path)

        assert modified == []
        assert "stale" in capsys.readouterr().out
