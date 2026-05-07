"""Tests for devtool.services.env_generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from devtool.domain.models import Service, ServiceType, VenvConfig, VenvStrategy
from devtool.services.env_generator import generate, check_placeholders, check_unresolved, _ENV_HEADER


def _make_service(
    name: str = "test-svc",
    env_file: str | None = ".env",
    env_entries: dict[str, str] | None = None,
) -> Service:
    return Service(
        name=name,
        directory=Path("svc"),
        type=ServiceType.PYTHON,
        launch="echo ok",
        venv=VenvConfig(strategy=VenvStrategy.NONE),
        env_file=env_file,
        env_entries=env_entries or {},
    )


class TestGenerate:
    def test_creates_env_file(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        svc = _make_service(env_entries={"KEY": "value", "OTHER": "123"})

        result = generate(svc, tmp_path)

        assert result is True
        env_path = svc_dir / ".env"
        assert env_path.exists()
        content = env_path.read_text()
        assert content.startswith(_ENV_HEADER)
        assert "KEY=value\n" in content
        assert "OTHER=123\n" in content

    def test_skips_existing_without_force(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        env_path = svc_dir / ".env"
        env_path.write_text("existing content")
        svc = _make_service(env_entries={"KEY": "value"})

        result = generate(svc, tmp_path)

        assert result is False
        assert env_path.read_text() == "existing content"

    def test_overwrites_with_force(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        env_path = svc_dir / ".env"
        env_path.write_text("old")
        svc = _make_service(env_entries={"KEY": "new"})

        result = generate(svc, tmp_path, force=True)

        assert result is True
        assert "KEY=new" in env_path.read_text()

    def test_no_env_file_returns_false(self, tmp_path: Path) -> None:
        svc = _make_service(env_file=None)
        assert generate(svc, tmp_path) is False

    def test_no_env_entries_returns_false(self, tmp_path: Path) -> None:
        svc = _make_service(env_entries={})
        assert generate(svc, tmp_path) is False


class TestGenerateLocalAuth:
    def test_identity_local_auth_skips_keycloak_keys(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        svc = _make_service(
            name="identity",
            env_entries={
                "keycloak_base_url": "https://keycloak.test",
                "client_id": "<REPLACE>",
                "client_secret": "<REPLACE>",
                "keycloak_realm": "master",
                "hostname_local": "127.0.0.1",
                "port": "13456",
            },
        )

        result = generate(svc, tmp_path, local_auth=True)

        assert result is True
        content = (svc_dir / ".env").read_text()
        assert "keycloak_base_url" not in content
        assert "client_id" not in content
        assert "client_secret" not in content
        assert "keycloak_realm" not in content
        assert "hostname_local=127.0.0.1\n" in content
        assert "port=13456\n" in content
        assert "local_auth_enabled=true\n" in content

    def test_identity_no_local_auth_writes_all_keys(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        svc = _make_service(
            name="identity",
            env_entries={
                "keycloak_base_url": "https://keycloak.test",
                "client_id": "<REPLACE>",
                "hostname_local": "127.0.0.1",
            },
        )

        result = generate(svc, tmp_path, local_auth=False)

        assert result is True
        content = (svc_dir / ".env").read_text()
        assert "keycloak_base_url=https://keycloak.test\n" in content
        assert "client_id=<REPLACE>\n" in content
        assert "hostname_local=127.0.0.1\n" in content
        assert "local_auth_enabled" not in content

    def test_non_identity_unaffected_by_local_auth(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        svc = _make_service(
            name="backend",
            env_entries={
                "client_id": "some-value",
                "hostname_local": "127.0.0.1",
            },
        )

        result = generate(svc, tmp_path, local_auth=True)

        assert result is True
        content = (svc_dir / ".env").read_text()
        assert "client_id=some-value\n" in content
        assert "hostname_local=127.0.0.1\n" in content
        assert "local_auth_enabled" not in content


class TestCheckPlaceholders:
    def test_no_placeholders_in_template(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        (svc_dir / ".env").write_text("KEY=real_value\nOTHER=123\n")
        svc = _make_service(env_entries={"KEY": "real_value"})

        assert check_placeholders(svc, tmp_path) == set()

    def test_detects_unreplaced_placeholder(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        (svc_dir / ".env").write_text(
            "client_id=<REPLACE_WITH_YOUR_CLIENT_ID>\n"
            "port=13456\n"
        )
        svc = _make_service(env_entries={
            "client_id": "<REPLACE_WITH_YOUR_CLIENT_ID>",
            "port": "13456",
        })

        result = check_placeholders(svc, tmp_path)
        assert result == {"client_id"}

    def test_multiple_placeholders(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        (svc_dir / ".env").write_text(
            "id=<REPLACE_ID>\nsecret=<replace_secret>\nhost=localhost\n"
        )
        svc = _make_service(env_entries={
            "id": "<REPLACE_ID>",
            "secret": "<replace_secret>",
            "host": "localhost",
        })

        assert check_placeholders(svc, tmp_path) == {"id", "secret"}

    def test_replaced_on_disk_not_flagged(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        (svc_dir / ".env").write_text("client_id=my_real_id\n")
        svc = _make_service(env_entries={
            "client_id": "<REPLACE_WITH_YOUR_CLIENT_ID>",
        })

        assert check_placeholders(svc, tmp_path) == set()

    def test_file_does_not_exist(self, tmp_path: Path) -> None:
        svc = _make_service(env_entries={"KEY": "<REPLACE>"})
        assert check_placeholders(svc, tmp_path) == set()

    def test_no_env_file_configured(self, tmp_path: Path) -> None:
        svc = _make_service(env_file=None)
        assert check_placeholders(svc, tmp_path) == set()

    def test_no_env_entries(self, tmp_path: Path) -> None:
        svc = _make_service(env_entries={})
        assert check_placeholders(svc, tmp_path) == set()

    def test_skips_comments_and_blank_lines(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        (svc_dir / ".env").write_text(
            "# <REPLACE this is a comment>\n"
            "\n"
            "KEY=good_value\n"
        )
        svc = _make_service(env_entries={"KEY": "<REPLACE_KEY>"})

        assert check_placeholders(svc, tmp_path) == set()
