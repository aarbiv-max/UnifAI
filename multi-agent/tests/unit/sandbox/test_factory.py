"""Unit tests for SandboxExecToolFactory."""
from unittest.mock import MagicMock
from dataclasses import dataclass, field
from typing import Optional

import pytest

from mas.elements.tools.sandbox_exec.sandbox_exec_factory import SandboxExecToolFactory
from mas.elements.tools.sandbox_exec.config import SandboxExecToolConfig
from mas.elements.tools.sandbox_exec.sandbox_exec import SandboxExecTool
from mas.elements.common.exceptions import PluginConfigurationError


def _make_config() -> SandboxExecToolConfig:
    return SandboxExecToolConfig(
        vm_host="10.0.0.1",
        vm_username="user",
        vm_password="pass",
    )


@dataclass
class FakeDeps:
    vm_sandbox_manager: Optional[MagicMock] = field(default=None)
    run_id: Optional[str] = field(default=None)


class TestSandboxExecToolFactory:

    def test_accepts_correct_type(self):
        factory = SandboxExecToolFactory()
        cfg = _make_config()
        assert factory.accepts(cfg, "sandbox_exec") is True
        assert factory.accepts(cfg, "ssh_exec") is False

    def test_create_with_deps(self):
        factory = SandboxExecToolFactory()
        cfg = _make_config()
        deps = FakeDeps(vm_sandbox_manager=MagicMock(), run_id="test-run-123")
        tool = factory.create(cfg, deps=deps)
        assert isinstance(tool, SandboxExecTool)
        assert tool._run_id == "test-run-123"

    def test_create_without_manager_raises(self):
        factory = SandboxExecToolFactory()
        cfg = _make_config()
        deps = FakeDeps(vm_sandbox_manager=None, run_id="x")
        with pytest.raises(PluginConfigurationError, match="VmSandboxManager"):
            factory.create(cfg, deps=deps)

    def test_create_without_deps_raises(self):
        factory = SandboxExecToolFactory()
        cfg = _make_config()
        with pytest.raises(PluginConfigurationError, match="VmSandboxManager"):
            factory.create(cfg)

    def test_create_fallback_run_id(self):
        factory = SandboxExecToolFactory()
        cfg = _make_config()
        deps = FakeDeps(vm_sandbox_manager=MagicMock(), run_id=None)
        tool = factory.create(cfg, deps=deps)
        assert len(tool._run_id) == 8
