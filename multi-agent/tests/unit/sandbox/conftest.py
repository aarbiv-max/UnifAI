"""Shared fixtures for sandbox unit tests."""
import pytest
from unittest.mock import Mock, MagicMock

from mas.core.execution_context import ExecutionContext, ExecutionContextHolder
from mas.elements.tools.sandbox_exec.config import SandboxExecToolConfig
from mas.elements.tools.sandbox_exec.models import SandboxPodInfo, SandboxState
from mas.elements.tools.sandbox_exec.ports import SandboxManagerPort


@pytest.fixture
def sandbox_config() -> SandboxExecToolConfig:
    return SandboxExecToolConfig(
        cluster_api="https://api.test-cluster.example.com:6443",
        cluster_token="test-token-abc123",
        namespace="sandbox-ns",
        git_repo_url="https://github.com/org/repo.git",
        git_token="ghp_test_token",
        skip_tls_verify=True,
    )


@pytest.fixture
def sandbox_config_public_repo() -> SandboxExecToolConfig:
    return SandboxExecToolConfig(
        cluster_api="https://api.cluster.example.com:6443",
        cluster_token="token-xyz",
        namespace="default",
        git_repo_url="https://github.com/public/repo.git",
        git_token="",
        skip_tls_verify=False,
    )


@pytest.fixture
def mock_sandbox_manager() -> Mock:
    return Mock(spec=SandboxManagerPort)


@pytest.fixture
def sample_run_id() -> str:
    return "run-abcdef12-3456-7890"


@pytest.fixture
def sample_agent_ids() -> list:
    return ["agent_1", "code_reviewer"]


@pytest.fixture
def sample_sandbox_state(sample_run_id: str) -> SandboxState:
    return SandboxState(
        session_id=sample_run_id,
        pvc_name="sandbox-pvc-run-abcd",
        cluster_api="https://api.test-cluster.example.com:6443",
        namespace="sandbox-ns",
        git_repo_url="https://github.com/org/repo.git",
        pods={
            "agent_1": SandboxPodInfo(
                agent_id="agent_1",
                pod_name="sandbox-run-abcd-agent_1",
                namespace="sandbox-ns",
                worktree_path="/workspace/worktree-agent_1",
                branch_name="sandbox/agent_1",
                status="ready",
            ),
            "code_reviewer": SandboxPodInfo(
                agent_id="code_reviewer",
                pod_name="sandbox-run-abcd-code_reviewer",
                namespace="sandbox-ns",
                worktree_path="/workspace/worktree-code_reviewer",
                branch_name="sandbox/code_reviewer",
                status="ready",
            ),
        },
    )


@pytest.fixture
def execution_ctx_holder() -> ExecutionContextHolder:
    holder = ExecutionContextHolder()
    holder.context = ExecutionContext(
        tags={"run_id": "run-abcd", "node_uid": "agent_1"},
    )
    return holder
