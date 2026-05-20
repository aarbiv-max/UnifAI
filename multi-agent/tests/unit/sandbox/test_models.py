"""Unit tests for sandbox runtime models."""
import pytest

from mas.elements.tools.sandbox_exec.models import SandboxContainerInfo, SandboxState


class TestSandboxContainerInfo:

    def test_default_status_is_provisioning(self):
        info = SandboxContainerInfo(
            agent_id="agent-1",
            container_name="sandbox-abc12345-agent-1",
            worktree_path="/opt/sandbox/wt-agent-1",
        )
        assert info.status == "provisioning"

    def test_explicit_status(self):
        info = SandboxContainerInfo(
            agent_id="a", container_name="c", worktree_path="/p",
            status="ready",
        )
        assert info.status == "ready"


class TestSandboxState:

    def test_empty_containers_by_default(self):
        state = SandboxState(session_id="run-1", vm_host="10.0.0.1")
        assert state.containers == {}

    def test_containers_keyed_by_agent_id(self):
        info = SandboxContainerInfo(
            agent_id="a1", container_name="c1", worktree_path="/wt1",
        )
        state = SandboxState(
            session_id="run-1",
            vm_host="10.0.0.1",
            containers={"a1": info},
        )
        assert "a1" in state.containers
        assert state.containers["a1"].container_name == "c1"
