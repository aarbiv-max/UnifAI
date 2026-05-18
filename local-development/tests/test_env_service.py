"""Tests for devtool.services.env_service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from devtool.domain.models import Service, ServiceType, VenvConfig, VenvStrategy
from devtool.services.env_service import EnvService


def _make_service(name: str = "backend") -> Service:
    return Service(
        name=name, directory=Path(name), type=ServiceType.PYTHON,
        launch="echo ok", venv=VenvConfig(strategy=VenvStrategy.NONE),
        env_file=".env", env_entries={"KEY": "val"},
    )


def _make_env_service(
    services: list[Service] | None = None,
    root: Path = Path("/fake"),
) -> EnvService:
    registry = MagicMock()
    svcs = services or [_make_service()]
    by_name = {s.name: s for s in svcs}
    registry.all_services.return_value = svcs
    registry.get_service.side_effect = lambda n: by_name[n]
    return EnvService(registry=registry, root=root)


class TestGenerate:
    @patch("devtool.services.env_service.env")
    def test_generate_prints_summary(self, mock_env, capsys) -> None:
        mock_env.generate_all.return_value = (["api"], ["backend"], ["rag"], [])
        svc = _make_env_service()

        svc.generate()

        captured = capsys.readouterr()
        assert "Generated: api" in captured.out
        assert "Updated" in captured.out
        assert "Preserved" in captured.out

    @patch("devtool.services.env_service.env")
    def test_generate_force(self, mock_env) -> None:
        mock_env.generate_all.return_value = ([], [], [], [])
        svc = _make_env_service()

        svc.generate(force=True)

        mock_env.generate_all.assert_called_once()
        _, kwargs = mock_env.generate_all.call_args
        assert kwargs["force"] is True

    @patch("devtool.services.env_service.env")
    def test_generate_prints_warnings(self, mock_env, capsys) -> None:
        mock_env.generate_all.return_value = ([], [], [], ["⚠ warning"])
        svc = _make_env_service()

        svc.generate()

        captured = capsys.readouterr()
        assert "⚠ warning" in captured.out


class TestShow:
    @patch("devtool.services.env_service.env")
    def test_show_delegates(self, mock_env) -> None:
        svc = _make_env_service()
        svc.show("backend")
        mock_env.show.assert_called_once()


class TestAutoResolveGeneratedKeys:
    @patch("devtool.services.env_service.env")
    def test_noop_when_no_keys(self, mock_env) -> None:
        mock_env.collect_auto_generate_keys.return_value = {}
        svc = _make_env_service()

        svc.auto_resolve_generated_keys()

        mock_env.resolve_auto_generate_key.assert_not_called()

    @patch("devtool.services.env_service.env")
    def test_resolves_keys(self, mock_env, capsys) -> None:
        mock_env.collect_auto_generate_keys.return_value = {
            "SECRET_KEY": ["backend", "api"],
        }
        mock_env.get_or_create_shared_secret.return_value = "s3cr3t"
        mock_env.resolve_auto_generate_key.return_value = 2

        svcs = [_make_service("backend"), _make_service("api")]
        svc = _make_env_service(svcs)

        svc.auto_resolve_generated_keys()

        mock_env.resolve_auto_generate_key.assert_called_once()
        captured = capsys.readouterr()
        assert "SECRET_KEY" in captured.out
        assert "2 service(s)" in captured.out


class TestResolvePlaceholders:
    @patch("devtool.services.env_service.env")
    def test_no_placeholders(self, mock_env, capsys) -> None:
        mock_env.check_unresolved.return_value = (set(), set())
        svc = _make_env_service()

        svc.resolve_placeholders(non_interactive=True)

        captured = capsys.readouterr()
        assert "No placeholders" in captured.out

    @patch("devtool.services.env_service.env")
    def test_non_interactive_warns(self, mock_env, capsys) -> None:
        mock_env.check_unresolved.return_value = ({"client_id"}, set())
        svc = _make_env_service()

        svc.resolve_placeholders(non_interactive=True)

        captured = capsys.readouterr()
        assert "client_id" in captured.out
        assert "placeholder" in captured.out
