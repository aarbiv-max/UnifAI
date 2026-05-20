"""Unit tests for SandboxExecTool — provisioning, execution, cleanup."""
import contextvars
import threading
from unittest.mock import MagicMock, call, patch

import pytest

from mas.elements.tools.sandbox_exec.config import SandboxExecToolConfig
from mas.elements.tools.sandbox_exec.sandbox_exec import (
    SandboxExecTool,
    _sanitize_name,
)
from mas.elements.tools.common.execution.context import caller_uid_var


def _make_tool(
    vm_mock: MagicMock,
    run_id: str = "abc12345",
    git_repo_url: str = "",
    workspace: str = "/opt/sandbox",
) -> SandboxExecTool:
    cfg = SandboxExecToolConfig(
        vm_host="10.0.0.1",
        vm_username="user",
        vm_password="pass",
        vm_workspace_path=workspace,
        git_repo_url=git_repo_url,
        git_branch="main",
        vm_container_image="python:3.11-slim",
        container_timeout=7200,
        container_network="none",
    )
    return SandboxExecTool(config=cfg, vm_sandbox_manager=vm_mock, run_id=run_id)


class TestSanitizeName:
    def test_alphanumeric(self):
        assert _sanitize_name("reviewer-1") == "reviewer-1"

    def test_special_chars(self):
        assert _sanitize_name("a@b.c/d") == "a-b-c-d"

    def test_empty_fallback(self):
        assert _sanitize_name("") == "default"


class TestSandboxExecToolProvisioning:
    """Test lazy provisioning logic."""

    def test_provision_no_git(self):
        vm = MagicMock()
        vm.run_command.return_value = (0, "", "")
        vm.execute_in_container.return_value = "hello"
        tool = _make_tool(vm)

        ctx = contextvars.copy_context()
        ctx.run(caller_uid_var.set, "agent-1")
        result = ctx.run(tool.run, cmd="echo hello", workdir="/workspace")

        vm.run_command.assert_any_call(
            "10.0.0.1", 22, "user", "pass",
            "mkdir -p /opt/sandbox/wt-agent-1",
        )
        vm.teardown_container.assert_called_once()
        vm.provision_container.assert_called_once()
        assert "[Workspace: /workspace]" in result

    def test_provision_with_git_existing_worktree(self):
        vm = MagicMock()
        vm.run_command.return_value = (0, "", "")
        vm.execute_in_container.return_value = "output"
        tool = _make_tool(vm, git_repo_url="https://github.com/org/repo.git")

        ctx = contextvars.copy_context()
        ctx.run(caller_uid_var.set, "agent-1")
        ctx.run(tool.run, cmd="ls", workdir="/workspace")

        vm.setup_bare_repo.assert_called_once()
        vm.create_worktree.assert_not_called()

    def test_provision_with_git_new_worktree(self):
        vm = MagicMock()
        vm.run_command.side_effect = [
            (1, "", ""),  # worktree doesn't exist
            (0, "", ""),  # verify worktree
        ]
        vm.execute_in_container.return_value = "output"
        tool = _make_tool(vm, git_repo_url="https://github.com/org/repo.git")

        ctx = contextvars.copy_context()
        ctx.run(caller_uid_var.set, "agent-2")
        ctx.run(tool.run, cmd="ls", workdir="/workspace")

        vm.create_worktree.assert_called_once()

    def test_idempotent_provisioning(self):
        vm = MagicMock()
        vm.run_command.return_value = (0, "", "")
        vm.execute_in_container.return_value = "ok"
        tool = _make_tool(vm)

        ctx = contextvars.copy_context()
        ctx.run(caller_uid_var.set, "agent-1")
        ctx.run(tool.run, cmd="cmd1", workdir="/workspace")
        ctx.run(tool.run, cmd="cmd2", workdir="/workspace")

        assert vm.provision_container.call_count == 1

    def test_different_agents_get_different_containers(self):
        vm = MagicMock()
        vm.run_command.return_value = (0, "", "")
        vm.execute_in_container.return_value = "ok"
        tool = _make_tool(vm)

        ctx1 = contextvars.copy_context()
        ctx1.run(caller_uid_var.set, "agent-1")
        ctx1.run(tool.run, cmd="cmd", workdir="/workspace")

        ctx2 = contextvars.copy_context()
        ctx2.run(caller_uid_var.set, "agent-2")
        ctx2.run(tool.run, cmd="cmd", workdir="/workspace")

        assert vm.provision_container.call_count == 2
        names = [c.kwargs["container_name"] for c in vm.provision_container.call_args_list]
        assert names[0] != names[1]
        assert "agent-1" in names[0]
        assert "agent-2" in names[1]


class TestWorkdirSanitization:
    def test_normal_path(self):
        assert SandboxExecTool._safe_workdir("/workspace/src") == "/workspace/src"

    def test_relative_path(self):
        assert SandboxExecTool._safe_workdir("src/app") == "/workspace/src/app"

    def test_traversal_blocked(self):
        assert SandboxExecTool._safe_workdir("../../etc/passwd") == "/workspace"

    def test_absolute_outside_workspace(self):
        assert SandboxExecTool._safe_workdir("/etc/passwd") == "/workspace"

    def test_workspace_root(self):
        assert SandboxExecTool._safe_workdir("/workspace") == "/workspace"


class TestCleanup:
    def test_cleanup_tears_down_all_containers(self):
        vm = MagicMock()
        vm.run_command.return_value = (0, "", "")
        vm.execute_in_container.return_value = "ok"
        tool = _make_tool(vm, run_id="run12345")

        ctx1 = contextvars.copy_context()
        ctx1.run(caller_uid_var.set, "a1")
        ctx1.run(tool.run, cmd="x", workdir="/workspace")

        ctx2 = contextvars.copy_context()
        ctx2.run(caller_uid_var.set, "a2")
        ctx2.run(tool.run, cmd="x", workdir="/workspace")

        vm.teardown_container.reset_mock()
        tool.cleanup()

        assert vm.teardown_container.call_count == 2
        assert len(tool._provisioned) == 0

    def test_cleanup_continues_on_failure(self):
        vm = MagicMock()
        vm.run_command.return_value = (0, "", "")
        vm.execute_in_container.return_value = "ok"
        tool = _make_tool(vm)

        ctx1 = contextvars.copy_context()
        ctx1.run(caller_uid_var.set, "a1")
        ctx1.run(tool.run, cmd="x", workdir="/workspace")

        ctx2 = contextvars.copy_context()
        ctx2.run(caller_uid_var.set, "a2")
        ctx2.run(tool.run, cmd="x", workdir="/workspace")

        vm.teardown_container.reset_mock()
        vm.teardown_container.side_effect = [RuntimeError("boom"), None]
        tool.cleanup()
        assert vm.teardown_container.call_count == 2


class TestCallerUidFallback:
    def test_empty_caller_uid_uses_default(self):
        vm = MagicMock()
        vm.run_command.return_value = (0, "", "")
        vm.execute_in_container.return_value = "ok"
        tool = _make_tool(vm)

        ctx = contextvars.copy_context()
        ctx.run(tool.run, cmd="x", workdir="/workspace")

        call_args = vm.provision_container.call_args
        assert "default" in call_args.kwargs["container_name"]
