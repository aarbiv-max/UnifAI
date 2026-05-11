"""Tests for SandboxExecToolFactory."""
import pytest
from unittest.mock import Mock

from mas.core.element_deps import ElementDeps
from mas.core.execution_context import ExecutionContextHolder
from mas.elements.tools.sandbox_exec.config import SandboxExecToolConfig
from mas.elements.tools.sandbox_exec.ports import SandboxManagerPort
from mas.elements.tools.sandbox_exec.sandbox_exec import SandboxExecTool
from mas.elements.tools.sandbox_exec.sandbox_exec_factory import SandboxExecToolFactory


class TestSandboxExecToolFactory:

    @pytest.fixture
    def factory(self):
        return SandboxExecToolFactory()

    def test_accepts_sandbox_exec_type(self, factory, sandbox_config):
        assert factory.accepts(sandbox_config, "sandbox_exec") is True

    def test_rejects_other_types(self, factory, sandbox_config):
        assert factory.accepts(sandbox_config, "oc_exec") is False
        assert factory.accepts(sandbox_config, "ssh_exec") is False

    def test_create_with_deps(self, factory, sandbox_config):
        holder = ExecutionContextHolder()
        manager = Mock(spec=SandboxManagerPort)
        deps = ElementDeps(
            execution_ctx=holder,
            sandbox_manager=manager,
        )

        tool = factory.create(sandbox_config, deps=deps)

        assert isinstance(tool, SandboxExecTool)
        assert tool._sandbox_manager is manager
        assert tool._execution_ctx is holder

    def test_create_without_deps(self, factory, sandbox_config):
        tool = factory.create(sandbox_config)

        assert isinstance(tool, SandboxExecTool)
        assert tool._sandbox_manager is None
        assert tool._execution_ctx is None
