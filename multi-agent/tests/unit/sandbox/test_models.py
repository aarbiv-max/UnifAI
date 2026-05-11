"""Tests for sandbox runtime models."""
import pytest

from mas.elements.tools.sandbox_exec.models import SandboxPodInfo, SandboxState


class TestSandboxPodInfo:

    def test_default_status_is_provisioning(self):
        pod = SandboxPodInfo(
            agent_id="a1",
            pod_name="sandbox-abc-a1",
            namespace="ns",
            worktree_path="/workspace/worktree-a1",
            branch_name="sandbox/a1",
        )
        assert pod.status == "provisioning"

    def test_explicit_status(self):
        pod = SandboxPodInfo(
            agent_id="a1",
            pod_name="sandbox-abc-a1",
            namespace="ns",
            worktree_path="/workspace/worktree-a1",
            branch_name="sandbox/a1",
            status="ready",
        )
        assert pod.status == "ready"


class TestSandboxState:

    def test_pods_default_empty(self):
        state = SandboxState(
            session_id="run-123",
            pvc_name="pvc-123",
            cluster_api="https://api",
            namespace="ns",
            git_repo_url="https://github.com/r.git",
        )
        assert state.pods == {}

    def test_serialization_roundtrip(self, sample_sandbox_state):
        data = sample_sandbox_state.model_dump()
        restored = SandboxState.model_validate(data)
        assert restored == sample_sandbox_state
        assert len(restored.pods) == 2
