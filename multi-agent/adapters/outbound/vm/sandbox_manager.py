from __future__ import annotations

import hashlib
import logging
import shlex
import threading
from typing import Dict, Tuple

from mas.core.sandbox.ports import VmConnectionInfo, VmSandboxManagerPort
from .ssh_client import SshClient

logger = logging.getLogger(__name__)


class VmSandboxManager(VmSandboxManagerPort):
    """Concrete adapter that manages VM sandboxes over SSH.

    Maintains a thread-safe cache of ``SshClient`` instances keyed by
    ``(host, port, username, password_hash)``.
    """

    def __init__(self) -> None:
        self._clients: Dict[Tuple[str, int, str, str], SshClient] = {}
        self._lock = threading.Lock()

    def validate_connectivity(
        self, conn: VmConnectionInfo, timeout: float = 10.0,
    ) -> bool:
        """Return True if the VM is reachable over SSH within *timeout* seconds."""
        try:
            client = self._get_client(conn)
            client.ensure_connected()
            return True
        except Exception:
            logger.warning(
                "Connectivity check failed for %s:%s", conn.host, conn.port,
            )
            return False

    def is_alive(self, conn: VmConnectionInfo) -> bool:
        """Quick liveness check (cached transport if available)."""
        try:
            client = self._get_client(conn)
            client.ensure_connected()
            exit_code, _, _ = client.exec_command("echo ok")
            return exit_code == 0
        except Exception:
            return False

    def run_command(
        self, conn: VmConnectionInfo, cmd: str,
    ) -> Tuple[int, str, str]:
        """Execute *cmd* on the VM and return ``(exit_code, stdout, stderr)``."""
        client = self._get_client(conn)
        return client.exec_command(cmd)

    def setup_bare_repo(
        self,
        conn: VmConnectionInfo,
        workspace_path: str,
        git_url: str,
        git_token: str = "",
    ) -> str:
        """Clone/fetch into a bare repo under *workspace_path* and return its path."""
        if git_token:
            authed_url = git_url.replace(
                "://", f"://oauth2:{git_token}@",
            )
        else:
            authed_url = git_url

        cmd = _build_setup_bare_repo_cmd(workspace_path, authed_url)
        client = self._get_client(conn)
        exit_code, stdout, stderr = client.exec_command(cmd)

        if git_token:
            stdout = stdout.replace(git_token, "***")
            stderr = stderr.replace(git_token, "***")

        if exit_code != 0:
            raise RuntimeError(
                f"setup_bare_repo failed (exit {exit_code}): {stderr}"
            )

        return stdout.strip()

    def create_worktree(
        self,
        conn: VmConnectionInfo,
        workspace_path: str,
        agent_id: str,
    ) -> str:
        """Create a git worktree for *agent_id* and return its path."""
        cmd = _build_create_worktree_cmd(workspace_path, agent_id)
        client = self._get_client(conn)
        exit_code, stdout, stderr = client.exec_command(cmd)
        if exit_code != 0:
            raise RuntimeError(
                f"create_worktree failed (exit {exit_code}): {stderr}"
            )
        return stdout.strip()

    def provision_container(
        self,
        conn: VmConnectionInfo,
        container_name: str,
        worktree_path: str,
        mount_path: str,
        image: str = "python:3.11-slim",
        timeout: int = 7200,
    ) -> str:
        """Start a Podman container and return its ID."""
        cmd = _build_provision_container_cmd(
            container_name, worktree_path, mount_path, image, timeout,
        )
        client = self._get_client(conn)
        exit_code, stdout, stderr = client.exec_command(cmd)
        if exit_code != 0:
            raise RuntimeError(
                f"provision_container failed (exit {exit_code}): {stderr}"
            )
        return stdout.strip()

    def teardown_container(
        self,
        conn: VmConnectionInfo,
        container_name: str,
    ) -> None:
        """Stop and remove the container."""
        cmd = _build_teardown_cmd(container_name)
        client = self._get_client(conn)
        exit_code, _, stderr = client.exec_command(cmd)
        if exit_code != 0:
            logger.warning(
                "teardown_container %s exited %d: %s",
                container_name, exit_code, stderr,
            )

    def execute_in_container(
        self,
        conn: VmConnectionInfo,
        container_name: str,
        cmd: str,
        workdir: str = "",
    ) -> str:
        """Run *cmd* inside an existing container and return combined output."""
        full_cmd = _build_exec_in_container_cmd(
            container_name, cmd, workdir,
        )
        client = self._get_client(conn)
        exit_code, stdout, stderr = client.exec_command(full_cmd)
        if exit_code != 0:
            raise RuntimeError(
                f"execute_in_container failed (exit {exit_code}): {stderr}"
            )
        return stdout + stderr

    def close_all(self) -> None:
        """Close every cached SSH client."""
        with self._lock:
            for key, client in self._clients.items():
                try:
                    client.close()
                except Exception:
                    logger.debug("Error closing client %s", key)
            self._clients.clear()

    def _get_client(self, conn: VmConnectionInfo) -> SshClient:
        key = _cache_key(conn)
        with self._lock:
            if key not in self._clients:
                self._clients[key] = SshClient(
                    host=conn.host,
                    port=conn.port,
                    username=conn.username,
                    password=conn.password,
                )
            return self._clients[key]


def _cache_key(conn: VmConnectionInfo) -> Tuple[str, int, str, str]:
    pw_hash = hashlib.sha256(
        conn.password.encode(),
    ).hexdigest()[:16]
    return (conn.host, conn.port, conn.username, pw_hash)


def _build_setup_bare_repo_cmd(workspace: str, url: str) -> str:
    ws = shlex.quote(workspace)
    u = shlex.quote(url)
    return (
        f"mkdir -p {ws} && "
        f"cd {ws} && "
        f"if [ -d repo.git ]; then "
        f"cd repo.git && git fetch --all; "
        f"else git clone --bare {u} repo.git; fi && "
        f"echo {ws}/repo.git"
    )


def _build_create_worktree_cmd(
    workspace: str, agent_id: str,
) -> str:
    ws = shlex.quote(workspace)
    wt_path = f"{workspace}/worktrees/{agent_id}"
    wt = shlex.quote(wt_path)
    return (
        f"cd {ws}/repo.git && "
        f"git worktree add {wt} HEAD 2>/dev/null || true && "
        f"echo {wt}"
    )


def _build_provision_container_cmd(
    name: str,
    worktree: str,
    mount: str,
    image: str,
    timeout: int,
) -> str:
    n = shlex.quote(name)
    w = shlex.quote(worktree)
    m = shlex.quote(mount)
    img = shlex.quote(image)
    return (
        f"podman run -d --name {n} "
        f"--timeout {int(timeout)} --network slirp4netns "
        f"-v {w}:{m}:Z "
        f"{img} sleep infinity"
    )


def _build_teardown_cmd(name: str) -> str:
    n = shlex.quote(name)
    return f"podman rm -f {n} 2>/dev/null || true"


def _build_exec_in_container_cmd(
    name: str, cmd: str, workdir: str,
) -> str:
    n = shlex.quote(name)
    inner = f"cd {shlex.quote(workdir)} && {cmd}" if workdir else cmd
    return f"podman exec {n} bash -c {shlex.quote(inner)}"
