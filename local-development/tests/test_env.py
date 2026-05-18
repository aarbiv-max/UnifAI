"""Tests for devtool.services.dotenv (environment file management)."""

from __future__ import annotations

from pathlib import Path

import pytest

from devtool.domain.models import Service, ServiceType, VenvConfig, VenvStrategy
from devtool.services.dotenv import (
    GenerateResult,
    align_local_auth,
    check_missing_keys,
    check_placeholders,
    check_unresolved,
    generate,
    replace_env_value,
)
from devtool.services.dotenv.common import ENV_HEADER


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

        assert result is GenerateResult.CREATED
        env_path = svc_dir / ".env"
        assert env_path.exists()
        content = env_path.read_text()
        assert content.startswith(ENV_HEADER)
        assert "KEY=value\n" in content
        assert "OTHER=123\n" in content

    def test_skips_existing_without_force(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        env_path = svc_dir / ".env"
        env_path.write_text("KEY=value\n")
        svc = _make_service(env_entries={"KEY": "value"})

        result = generate(svc, tmp_path)

        assert result is GenerateResult.SKIPPED
        assert env_path.read_text() == "KEY=value\n"

    def test_overwrites_with_force(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        env_path = svc_dir / ".env"
        env_path.write_text("old")
        svc = _make_service(env_entries={"KEY": "new"})

        result = generate(svc, tmp_path, force=True)

        assert result is GenerateResult.CREATED
        assert "KEY=new" in env_path.read_text()

    def test_no_env_file_returns_skipped(self, tmp_path: Path) -> None:
        svc = _make_service(env_file=None)
        assert generate(svc, tmp_path) is GenerateResult.SKIPPED

    def test_no_env_entries_returns_skipped(self, tmp_path: Path) -> None:
        svc = _make_service(env_entries={})
        assert generate(svc, tmp_path) is GenerateResult.SKIPPED


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

        assert result is GenerateResult.CREATED
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

        assert result is GenerateResult.CREATED
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

        assert result is GenerateResult.CREATED
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


class TestCheckMissingKeys:
    def test_detects_absent_keys(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        (svc_dir / ".env").write_text("KEY=value\n")
        svc = _make_service(env_entries={"KEY": "value", "OTHER": "123"})

        assert check_missing_keys(svc, tmp_path) == {"OTHER"}

    def test_none_missing(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        (svc_dir / ".env").write_text("KEY=value\nOTHER=123\n")
        svc = _make_service(env_entries={"KEY": "value", "OTHER": "123"})

        assert check_missing_keys(svc, tmp_path) == set()

    def test_file_does_not_exist(self, tmp_path: Path) -> None:
        svc = _make_service(env_entries={"KEY": "value"})
        assert check_missing_keys(svc, tmp_path) == set()

    def test_no_env_file_configured(self, tmp_path: Path) -> None:
        svc = _make_service(env_file=None, env_entries={"KEY": "value"})
        assert check_missing_keys(svc, tmp_path) == set()

    def test_respects_local_auth_for_identity(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        (svc_dir / ".env").write_text(
            "hostname_local=127.0.0.1\nlocal_auth_enabled=true\n"
        )
        svc = _make_service(
            name="identity",
            env_entries={
                "keycloak_base_url": "https://keycloak.test",
                "client_id": "<REPLACE>",
                "hostname_local": "127.0.0.1",
            },
        )
        missing = check_missing_keys(svc, tmp_path, local_auth=True)
        assert "keycloak_base_url" not in missing
        assert "client_id" not in missing
        assert missing == set()

    def test_skips_comments_and_blank_lines(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        (svc_dir / ".env").write_text(
            "# comment\n\nKEY=value\n"
        )
        svc = _make_service(env_entries={"KEY": "value", "OTHER": "123"})
        assert check_missing_keys(svc, tmp_path) == {"OTHER"}


class TestGenerateUpdate:
    def test_returns_updated_and_appends_missing(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        env_path = svc_dir / ".env"
        env_path.write_text("KEY=custom_value\n")
        svc = _make_service(env_entries={"KEY": "default", "NEW_KEY": "new_val"})

        result = generate(svc, tmp_path)

        assert result is GenerateResult.UPDATED
        content = env_path.read_text()
        assert "KEY=custom_value\n" in content
        assert "NEW_KEY=new_val\n" in content

    def test_preserves_existing_content(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        env_path = svc_dir / ".env"
        original = "# my custom header\nKEY=my_value\n"
        env_path.write_text(original)
        svc = _make_service(env_entries={"KEY": "default", "EXTRA": "extra_val"})

        generate(svc, tmp_path)

        content = env_path.read_text()
        assert content.startswith(original)
        assert "EXTRA=extra_val\n" in content

    def test_updated_respects_local_auth(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        env_path = svc_dir / ".env"
        env_path.write_text("hostname_local=127.0.0.1\nlocal_auth_enabled=true\n")
        svc = _make_service(
            name="identity",
            env_entries={
                "keycloak_base_url": "https://keycloak.test",
                "client_id": "<REPLACE>",
                "hostname_local": "127.0.0.1",
                "port": "13456",
            },
        )

        result = generate(svc, tmp_path, local_auth=True)

        assert result is GenerateResult.UPDATED
        content = env_path.read_text()
        assert "keycloak_base_url" not in content
        assert "client_id" not in content
        assert "port=13456\n" in content

    def test_skipped_when_all_keys_present(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        env_path = svc_dir / ".env"
        env_path.write_text("KEY=value\nOTHER=123\n")
        svc = _make_service(env_entries={"KEY": "value", "OTHER": "123"})

        result = generate(svc, tmp_path)

        assert result is GenerateResult.SKIPPED
        assert env_path.read_text() == "KEY=value\nOTHER=123\n"


class TestAlignLocalAuth:
    def test_adds_local_auth_enabled_when_missing(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        env_path = svc_dir / ".env"
        env_path.write_text("hostname_local=127.0.0.1\n")
        svc = _make_service(name="identity", env_entries={"hostname_local": "127.0.0.1"})

        assert align_local_auth(svc, tmp_path, local_auth=True) is True
        content = env_path.read_text()
        assert "local_auth_enabled=true\n" in content
        assert "hostname_local=127.0.0.1\n" in content

    def test_noop_when_already_present(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        env_path = svc_dir / ".env"
        original = "hostname_local=127.0.0.1\nlocal_auth_enabled=true\n"
        env_path.write_text(original)
        svc = _make_service(name="identity", env_entries={"hostname_local": "127.0.0.1"})

        assert align_local_auth(svc, tmp_path, local_auth=True) is False
        assert env_path.read_text() == original

    def test_removes_local_auth_enabled_when_false(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        env_path = svc_dir / ".env"
        env_path.write_text(
            "hostname_local=127.0.0.1\nlocal_auth_enabled=true\nport=13456\n"
        )
        svc = _make_service(name="identity", env_entries={"hostname_local": "127.0.0.1"})

        assert align_local_auth(svc, tmp_path, local_auth=False) is True
        content = env_path.read_text()
        assert "local_auth_enabled" not in content
        assert "hostname_local=127.0.0.1\n" in content
        assert "port=13456\n" in content

    def test_noop_when_already_absent(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        env_path = svc_dir / ".env"
        original = "hostname_local=127.0.0.1\n"
        env_path.write_text(original)
        svc = _make_service(name="identity", env_entries={"hostname_local": "127.0.0.1"})

        assert align_local_auth(svc, tmp_path, local_auth=False) is False
        assert env_path.read_text() == original

    def test_ignores_non_identity_service(self, tmp_path: Path) -> None:
        svc_dir = tmp_path / "svc"
        svc_dir.mkdir()
        env_path = svc_dir / ".env"
        env_path.write_text("KEY=value\n")
        svc = _make_service(name="backend", env_entries={"KEY": "value"})

        assert align_local_auth(svc, tmp_path, local_auth=True) is False
        assert env_path.read_text() == "KEY=value\n"

    def test_ignores_missing_file(self, tmp_path: Path) -> None:
        svc = _make_service(name="identity", env_entries={"KEY": "value"})
        assert align_local_auth(svc, tmp_path, local_auth=True) is False
