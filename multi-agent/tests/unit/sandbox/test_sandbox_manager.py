"""Unit tests for VmSandboxManager adapter."""
from unittest.mock import MagicMock, patch, call

import pytest

from outbound.vm.sandbox_manager import VmSandboxManager


class TestVmSandboxManagerClientCaching:
    """Test SSH client caching per (host, port, username) key."""

    def test_same_credentials_reuse_client(self):
        mgr = VmSandboxManager()
        with patch("outbound.vm.sandbox_manager.SshClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.exec_command.return_value = (0, "", "")
            mock_cls.return_value = mock_client

            mgr.run_command("h", 22, "u", "p", "ls")
            mgr.run_command("h", 22, "u", "p", "pwd")

            assert mock_cls.call_count == 1

    def test_different_hosts_get_different_clients(self):
        mgr = VmSandboxManager()
        with patch("outbound.vm.sandbox_manager.SshClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.exec_command.return_value = (0, "", "")
            mock_cls.return_value = mock_client

            mgr.run_command("host1", 22, "u", "p", "ls")
            mgr.run_command("host2", 22, "u", "p", "ls")

            assert mock_cls.call_count == 2


class TestVmSandboxManagerBareRepo:
    """Test bare repo setup."""

    def test_setup_bare_repo_skips_if_exists(self):
        mgr = VmSandboxManager()
        with patch("outbound.vm.sandbox_manager.SshClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.exec_command.return_value = (0, "", "")
            mock_cls.return_value = mock_client

            mgr.setup_bare_repo("h", 22, "u", "p", "/opt/repo.git", "https://gh/r", "")
            calls = mock_client.exec_command.call_args_list
            assert len(calls) == 1
            assert "test -d" in calls[0].args[0]

    def test_setup_bare_repo_clones_if_not_exists(self):
        mgr = VmSandboxManager()
        with patch("outbound.vm.sandbox_manager.SshClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.exec_command.side_effect = [
                (1, "", ""),  # test -d fails
                (0, "cloned", ""),  # git clone succeeds
            ]
            mock_cls.return_value = mock_client

            mgr.setup_bare_repo("h", 22, "u", "p", "/opt/repo.git", "https://gh/r", "")
            calls = mock_client.exec_command.call_args_list
            assert "git clone --bare" in calls[1].args[0]

    def test_setup_bare_repo_embeds_token(self):
        mgr = VmSandboxManager()
        with patch("outbound.vm.sandbox_manager.SshClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.exec_command.side_effect = [
                (1, "", ""),
                (0, "", ""),
            ]
            mock_cls.return_value = mock_client

            mgr.setup_bare_repo("h", 22, "u", "p", "/opt/r.git", "https://gh/r", "tok123")
            clone_cmd = mock_client.exec_command.call_args_list[1].args[0]
            assert "token:tok123@" in clone_cmd

    def test_setup_bare_repo_raises_on_failure(self):
        mgr = VmSandboxManager()
        with patch("outbound.vm.sandbox_manager.SshClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.exec_command.side_effect = [
                (1, "", ""),
                (128, "", "fatal: not a git repo"),
            ]
            mock_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="git clone --bare failed"):
                mgr.setup_bare_repo("h", 22, "u", "p", "/opt/r.git", "https://gh/r", "")


class TestVmSandboxManagerContainer:
    """Test container provisioning and teardown."""

    def test_provision_container_command(self):
        mgr = VmSandboxManager()
        with patch("outbound.vm.sandbox_manager.SshClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.exec_command.return_value = (0, "abc123", "")
            mock_cls.return_value = mock_client

            mgr.provision_container(
                "h", 22, "u", "p",
                container_name="sandbox-abc-agent1",
                host_worktree_path="/opt/wt-agent1",
                image="python:3.11-slim",
                timeout=7200,
                network="none",
            )

            cmd = mock_client.exec_command.call_args.args[0]
            assert "podman run -d" in cmd
            assert "--name sandbox-abc-agent1" in cmd
            assert "--timeout 7200" in cmd
            assert "--network=none" in cmd
            assert "-v /opt/wt-agent1:/workspace:Z" in cmd
            assert "sleep infinity" in cmd

    def test_provision_container_raises_on_failure(self):
        mgr = VmSandboxManager()
        with patch("outbound.vm.sandbox_manager.SshClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.exec_command.return_value = (125, "", "image not found")
            mock_cls.return_value = mock_client

            with pytest.raises(RuntimeError, match="podman run failed"):
                mgr.provision_container(
                    "h", 22, "u", "p", "c", "/w", "img", 100, "none",
                )

    def test_teardown_container_is_idempotent(self):
        mgr = VmSandboxManager()
        with patch("outbound.vm.sandbox_manager.SshClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.exec_command.return_value = (0, "", "")
            mock_cls.return_value = mock_client

            mgr.teardown_container("h", 22, "u", "p", "sandbox-xyz")
            cmd = mock_client.exec_command.call_args.args[0]
            assert "podman rm -f" in cmd
            assert "|| true" in cmd

    def test_execute_in_container(self):
        mgr = VmSandboxManager()
        with patch("outbound.vm.sandbox_manager.SshClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.exec_command.return_value = (0, "hello world", "")
            mock_cls.return_value = mock_client

            result = mgr.execute_in_container(
                "h", 22, "u", "p", "my-container", "echo hello", "/workspace",
            )
            assert result == "hello world"
            cmd = mock_client.exec_command.call_args.args[0]
            assert "podman exec my-container" in cmd
            assert "cd /workspace" in cmd

    def test_execute_in_container_returns_stderr_on_failure(self):
        mgr = VmSandboxManager()
        with patch("outbound.vm.sandbox_manager.SshClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.exec_command.return_value = (1, "partial", "error details")
            mock_cls.return_value = mock_client

            result = mgr.execute_in_container(
                "h", 22, "u", "p", "c", "bad_cmd", "/workspace",
            )
            assert "partial" in result
            assert "STDERR" in result
            assert "error details" in result


class TestVmSandboxManagerConnectivity:

    def test_validate_connectivity_success(self):
        mgr = VmSandboxManager()
        with patch("outbound.vm.sandbox_manager.SshClient") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            assert mgr.validate_connectivity("h", 22, "u", "p") is True

    def test_validate_connectivity_failure(self):
        mgr = VmSandboxManager()
        with patch("outbound.vm.sandbox_manager.SshClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.ensure_connected.side_effect = Exception("refused")
            mock_cls.return_value = mock_client
            assert mgr.validate_connectivity("h", 22, "u", "p") is False

    def test_is_alive_no_client(self):
        mgr = VmSandboxManager()
        assert mgr.is_alive("h", 22, "u", "p") is False
