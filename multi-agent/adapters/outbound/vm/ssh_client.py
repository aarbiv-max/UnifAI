"""Persistent SSH client with lazy reconnect and proactive keepalive.

Wraps paramiko to provide a reliable, long-lived SSH connection that
automatically recovers from idle-timeout drops and network interruptions.
"""
import logging
from typing import Callable, Optional, Tuple

import paramiko

logger = logging.getLogger(__name__)

_KEEPALIVE_INTERVAL = 60
_CONNECT_TIMEOUT = 30


class SshClient:
    """Persistent SSH connection to a single host.

    Reconnects lazily when the transport is found dead.
    Sends SSH keepalive packets every 60 s to prevent firewall drops.
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
        self._client: Optional[paramiko.SSHClient] = None

    # ── Connection management ───────────────────────────────────

    def _connect(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            look_for_keys=False,
            allow_agent=False,
            timeout=_CONNECT_TIMEOUT,
        )
        transport = self._client.get_transport()
        if transport is not None:
            transport.set_keepalive(_KEEPALIVE_INTERVAL)

        logger.debug("SSH connected to %s:%s", self._host, self._port)

    def _is_alive(self) -> bool:
        if self._client is None:
            return False
        transport = self._client.get_transport()
        if transport is None or not transport.is_active():
            return False
        try:
            transport.send_ignore()
            return True
        except Exception:
            return False

    def ensure_connected(self) -> None:
        """Guarantee an active SSH session, reconnecting if needed."""
        if not self._is_alive():
            self._connect()

    def close(self) -> None:
        """Explicitly close the SSH connection."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    # ── Command execution ───────────────────────────────────────

    def exec_command(self, cmd: str, timeout: int = 300) -> Tuple[int, str, str]:
        """Execute *cmd* and return ``(exit_code, stdout, stderr)``.

        Retries once on connection failure.
        """
        for attempt in range(2):
            try:
                self.ensure_connected()
                assert self._client is not None
                _, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)
                exit_code = stdout.channel.recv_exit_status()
                return (
                    exit_code,
                    stdout.read().decode(errors="replace"),
                    stderr.read().decode(errors="replace"),
                )
            except Exception:
                if attempt == 0:
                    logger.debug("SSH exec failed, reconnecting…", exc_info=True)
                    self._connect()
                else:
                    raise

        raise RuntimeError("Unreachable")

    def exec_command_streaming(
        self,
        cmd: str,
        callback: Callable[[str], None],
        timeout: int = 300,
    ) -> Tuple[int, str]:
        """Execute *cmd*, streaming stdout lines to *callback*.

        Returns ``(exit_code, full_output)``.
        """
        self.ensure_connected()
        assert self._client is not None
        _, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)

        lines = []
        for raw_line in stdout:
            line = raw_line.rstrip("\n")
            lines.append(line)
            callback(line)

        err = stderr.read().decode(errors="replace")
        if err:
            lines.append(err)
            callback(err)

        exit_code = stdout.channel.recv_exit_status()
        return exit_code, "\n".join(lines)
