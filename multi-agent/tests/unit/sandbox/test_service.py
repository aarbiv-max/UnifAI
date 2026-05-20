"""Unit tests for SandboxLifecycleService."""
import pytest
from unittest.mock import MagicMock, call

from mas.elements.tools.sandbox_exec.config import SandboxExecToolConfig
from mas.elements.tools.sandbox_exec.service import SandboxLifecycleService


@pytest.fixture
def mock_manager():
    mgr = MagicMock()
    mgr.run_command.return_value = (0, "", "")
    return mgr


@pytest.fixture
def config():
    return SandboxExecToolConfig(
        vm_host="10.0.0.1",
        vm_port=22,
        vm_username="user",
        vm_password="pass",
        vm_workspace_path="/opt/sandbox",
        git_repo_url="https://github.com/org/repo.git",
        git_token="tok",
    )


@pytest.fixture
def config_no_git():
    return SandboxExecToolConfig(
        vm_host="10.0.0.1",
        vm_port=22,
        vm_username="user",
        vm_password="pass",
        vm_workspace_path="/opt/sandbox",
    )


@pytest.fixture
def service(mock_manager):
    return SandboxLifecycleService(sandbox_manager=mock_manager)


class TestProvisionForSession:

    def test_provisions_workspace_dir(self, service, mock_manager, config):
        service.provision_for_session("run-1", ["agent-a"], config)
        mock_manager.run_command.assert_any_call(
            "10.0.0.1", 22, "user", "pass", "mkdir -p /opt/sandbox",
        )

    def test_sets_up_bare_repo_when_git_url_provided(self, service, mock_manager, config):
        service.provision_for_session("run-1", ["agent-a"], config)
        mock_manager.setup_bare_repo.assert_called_once_with(
            "10.0.0.1", 22, "user", "pass",
            bare_repo_path="/opt/sandbox/repo.git",
            git_repo_url="https://github.com/org/repo.git",
            git_token="tok",
        )

    def test_creates_worktree_per_agent(self, service, mock_manager, config):
        service.provision_for_session("run-1", ["agent-a", "agent-b"], config)
        assert mock_manager.create_worktree.call_count == 2

    def test_provisions_container_per_agent(self, service, mock_manager, config):
        state = service.provision_for_session("run-1", ["agent-a", "agent-b"], config)
        assert mock_manager.provision_container.call_count == 2
        assert len(state.containers) == 2
        assert state.containers["agent-a"].status == "ready"
        assert state.containers["agent-b"].status == "ready"

    def test_container_name_includes_run_id_prefix(self, service, mock_manager, config):
        state = service.provision_for_session("run-12345678", ["agent-a"], config)
        assert state.containers["agent-a"].container_name == "sandbox-run-1234-agent-a"

    def test_no_bare_repo_when_no_git_url(self, service, mock_manager, config_no_git):
        service.provision_for_session("run-1", ["agent-a"], config_no_git)
        mock_manager.setup_bare_repo.assert_not_called()
        mock_manager.create_worktree.assert_not_called()
        mock_manager.run_command.assert_any_call(
            "10.0.0.1", 22, "user", "pass", "mkdir -p /opt/sandbox/wt-agent-a",
        )

    def test_teardown_before_provision(self, service, mock_manager, config):
        service.provision_for_session("run-1", ["agent-a"], config)
        mock_manager.teardown_container.assert_called()


class TestTeardownByNaming:

    def test_deterministic_naming(self, service, mock_manager, config):
        service.teardown_by_naming("run-12345678", ["agent-a", "agent-b"], config)
        calls = mock_manager.teardown_container.call_args_list
        names = [c[0][4] for c in calls]
        assert "sandbox-run-1234-agent-a" in names
        assert "sandbox-run-1234-agent-b" in names

    def test_continues_on_error(self, service, mock_manager, config):
        mock_manager.teardown_container.side_effect = [RuntimeError("fail"), None]
        service.teardown_by_naming("run-1", ["a", "b"], config)
        assert mock_manager.teardown_container.call_count == 2
