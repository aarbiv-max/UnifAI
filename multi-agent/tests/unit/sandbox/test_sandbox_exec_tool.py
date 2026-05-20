"""Unit tests for the rewritten SandboxExecTool."""
import pytest
from unittest.mock import MagicMock

from mas.core.execution_context import ExecutionContext, ExecutionContextHolder
from mas.elements.tools.sandbox_exec.config import SandboxExecToolConfig
from mas.elements.tools.sandbox_exec.sandbox_exec import SandboxExecTool


@pytest.fixture
def config():
    return SandboxExecToolConfig(
        vm_host="10.0.0.1",
        vm_port=22,
        vm_username="user",
        vm_password="pass",
        vm_workspace_path="/opt/sandbox",
    )


@pytest.fixture
def mock_manager():
    mgr = MagicMock()
    mgr.execute_in_container.return_value = "hello world"
    return mgr


@pytest.fixture
def execution_ctx():
    holder = ExecutionContextHolder()
    holder.context = ExecutionContext(tags={
        "run_id": "run-12345678",
        "node_uid": "agent-alpha",
    })
    return holder


@pytest.fixture
def tool(mock_manager, config, execution_ctx):
    return SandboxExecTool(
        sandbox_manager=mock_manager,
        config=config,
        execution_ctx=execution_ctx,
    )


class TestSandboxExecTool:

    def test_run_reads_node_uid_from_tags(self, tool, mock_manager):
        result = tool.run(cmd="echo hi")
        call_kwargs = mock_manager.execute_in_container.call_args
        assert "sandbox-run-1234-agent-alpha" in call_kwargs[1]["container_name"] or \
               call_kwargs[0][4] == "sandbox-run-1234-agent-alpha"

    def test_run_returns_output_with_workspace(self, tool):
        result = tool.run(cmd="echo hi")
        assert "hello world" in result
        assert "[Workspace:" in result

    def test_run_uses_sanitized_uid_in_container_name(self, tool, mock_manager, execution_ctx):
        execution_ctx.context = ExecutionContext(tags={
            "run_id": "run-12345678",
            "node_uid": "Agent_Node.1",
        })
        tool.run(cmd="test")
        args = mock_manager.execute_in_container.call_args
        container_name = args[1].get("container_name") or args[0][4]
        assert container_name == "sandbox-run-1234-agent-node-1"

    def test_default_uid_fallback_with_warning(self, tool, mock_manager, execution_ctx):
        execution_ctx.context = ExecutionContext(tags={
            "run_id": "run-12345678",
        })
        result = tool.run(cmd="test")
        args = mock_manager.execute_in_container.call_args
        container_name = args[1].get("container_name") or args[0][4]
        assert "default" in container_name

    def test_safe_workdir_prevents_traversal(self, tool):
        result = tool._safe_workdir("../../etc/passwd")
        assert result == "/opt/sandbox"

    def test_safe_workdir_allows_subpath(self, tool):
        result = tool._safe_workdir("code/src")
        assert result == "/opt/sandbox/code/src"

    def test_cleanup_is_noop(self, tool):
        tool.cleanup()

    def test_tool_name_includes_host(self, tool):
        assert "10-0-0-1" in tool.name
        assert "22" in tool.name

    def test_execution_error_returns_message(self, tool, mock_manager):
        mock_manager.execute_in_container.side_effect = RuntimeError("connection lost")
        result = tool.run(cmd="fail")
        assert "Sandbox execution error" in result
