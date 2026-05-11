"""Tests for SandboxExecTool."""
import pytest
from unittest.mock import Mock

from mas.core.execution_context import ExecutionContext, ExecutionContextHolder
from mas.elements.tools.sandbox_exec.config import SandboxExecToolConfig
from mas.elements.tools.sandbox_exec.ports import SandboxManagerPort
from mas.elements.tools.sandbox_exec.sandbox_exec import SandboxExecTool


class TestSandboxExecTool:

    @pytest.fixture
    def tool(self, mock_sandbox_manager, sandbox_config, execution_ctx_holder):
        return SandboxExecTool(
            sandbox_manager=mock_sandbox_manager,
            config=sandbox_config,
            execution_ctx=execution_ctx_holder,
        )

    def test_run_delegates_to_manager(self, tool, mock_sandbox_manager):
        mock_sandbox_manager.execute.return_value = "hello world"

        result = tool.run(cmd="echo hello")

        mock_sandbox_manager.execute.assert_called_once()
        assert result == "hello world"

    def test_run_derives_pod_name_from_context(self, tool, mock_sandbox_manager):
        mock_sandbox_manager.execute.return_value = "ok"

        tool.run(cmd="ls")

        call_kwargs = mock_sandbox_manager.execute.call_args
        assert call_kwargs.kwargs["pod_name"] == "sandbox-run-abcd-agent_1"

    def test_run_uses_worktree_as_default_workdir(self, tool, mock_sandbox_manager):
        mock_sandbox_manager.execute.return_value = "ok"

        tool.run(cmd="ls")

        call_kwargs = mock_sandbox_manager.execute.call_args
        assert call_kwargs.kwargs["workdir"] == "/workspace/worktree-agent_1"

    def test_run_workdir_override(self, tool, mock_sandbox_manager):
        mock_sandbox_manager.execute.return_value = "ok"

        tool.run(cmd="ls", workdir="/tmp")

        call_kwargs = mock_sandbox_manager.execute.call_args
        assert call_kwargs.kwargs["workdir"] == "/tmp"

    def test_run_passes_cluster_config(self, tool, mock_sandbox_manager, sandbox_config):
        mock_sandbox_manager.execute.return_value = "ok"

        tool.run(cmd="ls")

        call_kwargs = mock_sandbox_manager.execute.call_args
        assert call_kwargs.kwargs["namespace"] == sandbox_config.namespace
        assert call_kwargs.kwargs["cluster_api"] == sandbox_config.cluster_api
        assert call_kwargs.kwargs["token"] == sandbox_config.cluster_token
        assert call_kwargs.kwargs["skip_tls_verify"] == sandbox_config.skip_tls_verify

    def test_run_returns_error_message_on_exception(self, tool, mock_sandbox_manager):
        mock_sandbox_manager.execute.side_effect = RuntimeError("connection refused")

        result = tool.run(cmd="ls")

        assert "Sandbox execution error" in result
        assert "connection refused" in result

    def test_different_node_uid_produces_different_pod(
        self, mock_sandbox_manager, sandbox_config
    ):
        """Verify two different nodes get routed to different pods."""
        holder1 = ExecutionContextHolder()
        holder1.context = ExecutionContext(
            tags={"run_id": "run-abcd", "node_uid": "agent_1"},
        )
        holder2 = ExecutionContextHolder()
        holder2.context = ExecutionContext(
            tags={"run_id": "run-abcd", "node_uid": "reviewer"},
        )

        tool1 = SandboxExecTool(
            sandbox_manager=mock_sandbox_manager, config=sandbox_config,
            execution_ctx=holder1,
        )
        tool2 = SandboxExecTool(
            sandbox_manager=mock_sandbox_manager, config=sandbox_config,
            execution_ctx=holder2,
        )

        mock_sandbox_manager.execute.return_value = "ok"
        tool1.run(cmd="ls")
        tool2.run(cmd="ls")

        calls = mock_sandbox_manager.execute.call_args_list
        assert calls[0].kwargs["pod_name"] == "sandbox-run-abcd-agent_1"
        assert calls[1].kwargs["pod_name"] == "sandbox-run-abcd-reviewer"
