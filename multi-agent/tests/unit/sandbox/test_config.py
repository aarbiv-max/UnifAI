"""Unit tests for SandboxExecToolConfig."""
import pytest
from pydantic import ValidationError

from mas.elements.tools.sandbox_exec.config import SandboxExecToolConfig


class TestSandboxExecToolConfig:
    """Validate config schema, defaults, and field constraints."""

    def test_minimal_valid_config(self):
        cfg = SandboxExecToolConfig(
            vm_host="10.0.0.1",
            vm_username="user",
            vm_password="pass",
        )
        assert cfg.type == "sandbox_exec"
        assert cfg.vm_port == 22
        assert cfg.vm_workspace_path == "/opt/sandbox"
        assert cfg.git_repo_url == ""
        assert cfg.git_branch == "main"
        assert cfg.vm_container_image == "python:3.11-slim"
        assert cfg.container_timeout == 7200
        assert cfg.container_network == "none"

    def test_full_config(self):
        cfg = SandboxExecToolConfig(
            vm_host="192.168.1.100",
            vm_port=2222,
            vm_username="admin",
            vm_password="s3cret",
            vm_workspace_path="/home/sandbox/ws",
            git_repo_url="https://github.com/org/repo.git",
            git_branch="develop",
            git_token="ghp_abc123",
            vm_container_image="node:18-alpine",
            container_timeout=3600,
            container_network="bridge",
        )
        assert cfg.vm_port == 2222
        assert cfg.git_branch == "develop"
        assert cfg.container_network == "bridge"

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            SandboxExecToolConfig(vm_host="10.0.0.1", vm_username="user")

    def test_type_discriminator(self):
        cfg = SandboxExecToolConfig(
            vm_host="h", vm_username="u", vm_password="p",
        )
        assert cfg.type == "sandbox_exec"

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            SandboxExecToolConfig(
                vm_host="h", vm_username="u", vm_password="p",
                unknown_field="x",
            )
