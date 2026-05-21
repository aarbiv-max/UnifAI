from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple

import paramiko

logger = logging.getLogger(__name__)


class SshClient:
    """Persistent SSH connection wrapper around paramiko.

    The connection is established lazily on first use and kept alive
    with periodic keep-alives.  If the transport dies between calls
    the client reconnects transparently.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._ssh: Optional[paramiko.SSHClient] = None

    def ensure_connected(self) -> None:
        """Establish or re-establish the SSH connection if needed."""
        if self._ssh is not None:
            transport = self._ssh.get_transport()
            if transport is not None and transport.is_active():
                return
            self._close_quietly()

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            look_for_keys=False,
            allow_agent=False,
            timeout=30,
        )
        transport = client.get_transport()
        if transport is not None:
            transport.set_keepalive(60)
        self._ssh = client
        logger.info("SSH connection established to %s:%s", self._host, self._port)

    def exec_command(self, cmd: str) -> Tuple[int, str, str]:
        """Execute *cmd* and return ``(exit_code, stdout, stderr)``.

        On transport failure the client reconnects and retries once.
        """
        try:
            return self._exec(cmd)
        except (paramiko.SSHException, OSError) as exc:
            logger.warning(
                "SSH command failed (%s), reconnecting and retrying", exc,
            )
            self._close_quietly()
            self.ensure_connected()
            return self._exec(cmd)

    def exec_command_streaming(
        self,
        cmd: str,
        callback: Callable[[str], None],
    ) -> int:
        """Execute *cmd*, stream stdout lines to *callback*, return exit code."""
        self.ensure_connected()
        assert self._ssh is not None
        _, stdout, _ = self._ssh.exec_command(cmd)
        for line in iter(stdout.readline, ""):
            callback(line.rstrip("\n"))
        return stdout.channel.recv_exit_status()

    def close(self) -> None:
        """Close the underlying SSH connection."""
        self._close_quietly()
        logger.debug("SSH client closed for %s:%s", self._host, self._port)

    def _exec(self, cmd: str) -> Tuple[int, str, str]:
        self.ensure_connected()
        assert self._ssh is not None
        _, stdout, stderr = self._ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        return exit_code, stdout.read().decode(), stderr.read().decode()

    def _close_quietly(self) -> None:
        if self._ssh is not None:
            try:
                self._ssh.close()
            except Exception:
                pass
            self._ssh = None
