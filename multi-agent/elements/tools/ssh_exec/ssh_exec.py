"""
Async-native SSH execution tool using asyncssh.

Uses a persistent connection with lazy initialization. Safe for parallel
execution: asyncssh multiplexes channels over a single transport within
the event loop, so concurrent arun() calls do not race.
"""
import asyncio
from typing import Any, Optional

import asyncssh
from pydantic import BaseModel, Field

from elements.tools.common.base_tool import BaseTool
from global_utils.utils.async_bridge import get_async_bridge

# Default timeouts (seconds)
_CONNECT_TIMEOUT = 30
_COMMAND_TIMEOUT = 120


class CommandInput(BaseModel):
    cmd: str = Field(..., description="Shell command to run on the VM")


class SshExecTool(BaseTool):
    """
    Async-native SSH command execution with persistent connection.

    Key design choices:
    - Connection is lazily established on first arun() call (async connect
      cannot happen inside __init__).
    - A single asyncssh connection is shared across concurrent arun() calls.
      This is safe because asyncssh multiplexes SSH channels over one
      transport inside the same event loop — no threads involved.
    - An asyncio.Lock guards only connection creation/teardown so that
      exactly one coroutine performs the handshake; all others wait and
      then reuse the established connection.
    - run() is a thin sync wrapper (via AsyncBridge) for the rare case
      where a sync caller exists. The primary execution path is arun().
    """

    name: str = "SshExecTool"
    description: str = "Execute a shell command on a remote VM via SSH"
    args_schema = CommandInput

    def __init__(self, *, host: str, port: int, username: str, password: str):
        super().__init__()
        self._host = host
        self._port = port
        self._username = username
        self._password = password

        # Lazy async connection — created on first arun() call
        self._conn: Optional[asyncssh.SSHClientConnection] = None
        self._lock = asyncio.Lock()

        # Build a unique, filesystem-safe tool name
        translation = str.maketrans(".:- /", "_____")
        safe_host = host.translate(translation)
        safe_username = username.translate(translation)
        self.name = f"ssh_exec_{safe_host}_{port}_{safe_username}"

        self.description = (
            f"Run shell commands on remote server at {host}:{port}.\n\n"
            f"This tool automatically connects to the server (as user '{username}') "
            f"and executes the command you provide. You only need to specify the command — "
            f"the tool handles the SSH connection, authentication, and execution.\n\n"
            f"Connection Details:\n"
            f"• Host: {host}\n"
            f"• Port: {port}\n"
            f"• User: {username}\n\n"
            f"Usage: Simply provide the shell command as an argument. "
            f"The tool will connect to this specific remote machine and run it."
        )

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def _connect(self) -> asyncssh.SSHClientConnection:
        """Create a new asyncssh connection with proper timeouts."""
        return await asyncio.wait_for(
            asyncssh.connect(
                self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                known_hosts=None,           # equivalent to paramiko AutoAddPolicy
                login_timeout=_CONNECT_TIMEOUT,
            ),
            timeout=_CONNECT_TIMEOUT,
        )

    def _is_connected(self) -> bool:
        """
        Check if the SSH connection is still alive.

        asyncssh does not expose a public is_closed() method.
        The internal _transport attribute is set to None when the
        connection is lost or explicitly closed.
        """
        if self._conn is None:
            return False
        try:
            # pylint: disable=protected-access
            return self._conn._transport is not None
        except Exception:
            return False

    async def _ensure_connected(self) -> asyncssh.SSHClientConnection:
        """
        Return the existing connection or create a new one.

        The lock guarantees that only one coroutine performs the SSH
        handshake; all others await and then share the result.
        Once the connection exists and is healthy, the lock is not
        contended — concurrent arun() calls proceed without waiting.
        """
        # Fast path (no lock): connection exists and is alive
        if self._is_connected():
            return self._conn  # type: ignore[return-value]

        # Slow path: acquire lock, double-check, reconnect if needed
        async with self._lock:
            # Double-check after acquiring the lock (another coroutine
            # may have reconnected while we were waiting).
            if self._is_connected():
                return self._conn  # type: ignore[return-value]

            # Discard stale connection if any
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

            self._conn = await self._connect()
            return self._conn

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def arun(self, *args: Any, **kwargs: Any) -> str:
        """
        Native async execution — no thread pool involved.

        Concurrent calls safely multiplex over the same connection
        because asyncssh opens a new SSH channel per run() call.
        Each command is protected by a timeout so a single hanging
        command cannot block the entire agent.
        """
        inp = self.args_schema(**kwargs)

        try:
            conn = await self._ensure_connected()
            result = await conn.run(
                inp.cmd, check=False, timeout=_COMMAND_TIMEOUT,
            )
            return self._format_result(result)
        except Exception:
            # Connection may have gone stale — reset and retry once.
            # Only one coroutine should perform the reconnect; others
            # will pick up the new connection via _ensure_connected().
            async with self._lock:
                if self._conn is not None:
                    try:
                        self._conn.close()
                    except Exception:
                        pass
                    self._conn = None

            try:
                conn = await self._ensure_connected()
                result = await conn.run(
                    inp.cmd, check=False, timeout=_COMMAND_TIMEOUT,
                )
                return self._format_result(result)
            except Exception as retry_error:
                return (
                    f"ERROR: Failed to execute command even after "
                    f"reconnection: {retry_error}"
                )

    def run(self, *args: Any, **kwargs: Any) -> str:
        """
        Synchronous fallback — delegates to arun() via AsyncBridge.

        Only used when no event loop is running (e.g. tests, CLI).
        The primary production path goes through arun() directly.
        """
        try:
            with get_async_bridge() as bridge:
                return bridge.run(self.arun(*args, **kwargs))
        except Exception as e:
            return f"ERROR: Synchronous SSH execution failed: {e}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_result(result: asyncssh.SSHCompletedProcess) -> str:
        """Format command output, preferring stdout unless stderr is present."""
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        if err:
            return f"STDERR:\n{err}"
        return out

    async def close(self) -> None:
        """Explicitly close the SSH connection."""
        async with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    def __del__(self) -> None:
        """Best-effort cleanup when the tool is garbage collected."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
