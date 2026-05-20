"""Unit tests for SshClient — persistent SSH with lazy reconnect."""
from unittest.mock import MagicMock, patch, PropertyMock, call
import paramiko
import pytest

from outbound.vm.ssh_client import SshClient, _KEEPALIVE_INTERVAL


class TestSshClientConnection:
    """Test connection management."""

    @patch("outbound.vm.ssh_client.paramiko.SSHClient")
    def test_connect_sets_keepalive(self, mock_ssh_cls):
        mock_client = MagicMock()
        mock_transport = MagicMock()
        mock_client.get_transport.return_value = mock_transport
        mock_ssh_cls.return_value = mock_client

        client = SshClient("10.0.0.1", 22, "user", "pass")
        client._connect()

        mock_client.connect.assert_called_once_with(
            hostname="10.0.0.1", port=22, username="user", password="pass",
            look_for_keys=False, allow_agent=False, timeout=30,
        )
        mock_transport.set_keepalive.assert_called_once_with(_KEEPALIVE_INTERVAL)

    @patch("outbound.vm.ssh_client.paramiko.SSHClient")
    def test_connect_adds_auto_add_policy(self, mock_ssh_cls):
        mock_client = MagicMock()
        mock_client.get_transport.return_value = MagicMock()
        mock_ssh_cls.return_value = mock_client

        client = SshClient("h", 22, "u", "p")
        client._connect()

        mock_client.set_missing_host_key_policy.assert_called_once()

    @patch("outbound.vm.ssh_client.paramiko.SSHClient")
    def test_is_alive_false_when_no_client(self, mock_ssh_cls):
        client = SshClient("h", 22, "u", "p")
        assert client._is_alive() is False

    @patch("outbound.vm.ssh_client.paramiko.SSHClient")
    def test_is_alive_true_when_transport_active(self, mock_ssh_cls):
        mock_client_inst = MagicMock()
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_client_inst.get_transport.return_value = mock_transport
        mock_ssh_cls.return_value = mock_client_inst

        client = SshClient("h", 22, "u", "p")
        client._connect()
        assert client._is_alive() is True

    @patch("outbound.vm.ssh_client.paramiko.SSHClient")
    def test_is_alive_false_when_send_ignore_fails(self, mock_ssh_cls):
        mock_client_inst = MagicMock()
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_transport.send_ignore.side_effect = Exception("dead")
        mock_client_inst.get_transport.return_value = mock_transport
        mock_ssh_cls.return_value = mock_client_inst

        client = SshClient("h", 22, "u", "p")
        client._connect()
        assert client._is_alive() is False

    @patch("outbound.vm.ssh_client.paramiko.SSHClient")
    def test_ensure_connected_reconnects_when_dead(self, mock_ssh_cls):
        mock_client_inst = MagicMock()
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_client_inst.get_transport.return_value = mock_transport
        mock_ssh_cls.return_value = mock_client_inst

        client = SshClient("h", 22, "u", "p")
        client.ensure_connected()
        assert mock_client_inst.connect.call_count == 1

        client.ensure_connected()
        assert mock_client_inst.connect.call_count == 1

    @patch("outbound.vm.ssh_client.paramiko.SSHClient")
    def test_close(self, mock_ssh_cls):
        mock_client_inst = MagicMock()
        mock_client_inst.get_transport.return_value = MagicMock()
        mock_ssh_cls.return_value = mock_client_inst

        client = SshClient("h", 22, "u", "p")
        client._connect()
        client.close()
        mock_client_inst.close.assert_called_once()
        assert client._client is None


class TestSshClientExecCommand:
    """Test command execution with retry."""

    @patch("outbound.vm.ssh_client.paramiko.SSHClient")
    def test_exec_command_returns_tuple(self, mock_ssh_cls):
        mock_stdout = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"hello"
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_client_inst = MagicMock()
        mock_client_inst.exec_command.return_value = (None, mock_stdout, mock_stderr)
        mock_client_inst.get_transport.return_value = MagicMock()
        mock_ssh_cls.return_value = mock_client_inst

        client = SshClient("h", 22, "u", "p")
        exit_code, out, err = client.exec_command("echo hello")
        assert exit_code == 0
        assert out == "hello"
        assert err == ""

    @patch("outbound.vm.ssh_client.paramiko.SSHClient")
    def test_exec_command_retries_on_failure(self, mock_ssh_cls):
        mock_client_inst = MagicMock()
        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_client_inst.get_transport.return_value = mock_transport

        mock_stdout = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"ok"
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""

        mock_client_inst.exec_command.side_effect = [
            Exception("connection lost"),
            (None, mock_stdout, mock_stderr),
        ]
        mock_ssh_cls.return_value = mock_client_inst

        client = SshClient("h", 22, "u", "p")
        exit_code, out, err = client.exec_command("ls")
        assert exit_code == 0
        assert out == "ok"
        assert mock_client_inst.connect.call_count >= 2
