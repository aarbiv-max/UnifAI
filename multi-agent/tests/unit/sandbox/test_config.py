"""Tests for SandboxExecToolConfig."""
import pytest
from pydantic import ValidationError

from mas.elements.tools.sandbox_exec.config import SandboxExecToolConfig


class TestSandboxExecToolConfig:

    def test_type_discriminator(self, sandbox_config):
        assert sandbox_config.type == "sandbox_exec"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            SandboxExecToolConfig()

    def test_git_token_defaults_empty(self):
        cfg = SandboxExecToolConfig(
            cluster_api="https://api.example.com:6443",
            cluster_token="tok",
            namespace="ns",
            git_repo_url="https://github.com/r.git",
        )
        assert cfg.git_token == ""

    def test_skip_tls_defaults_false(self):
        cfg = SandboxExecToolConfig(
            cluster_api="https://api.example.com:6443",
            cluster_token="tok",
            namespace="ns",
            git_repo_url="https://github.com/r.git",
        )
        assert cfg.skip_tls_verify is False

    def test_serialization_roundtrip(self, sandbox_config):
        data = sandbox_config.model_dump()
        restored = SandboxExecToolConfig.model_validate(data)
        assert restored == sandbox_config

    def test_json_schema_includes_type(self):
        schema = SandboxExecToolConfig.model_json_schema()
        assert "type" in schema.get("properties", {})
