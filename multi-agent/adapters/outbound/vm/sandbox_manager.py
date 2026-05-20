"""Concrete adapter for VmSandboxManagerPort using SSH + Podman.

All VM interaction goes through SshClient.  This adapter is stateless
at construction time — SSH connections are created lazily and cached
per (host, port, username) key.
"""
import logging
import shlex
from typing import Callable, Dict, Optional, Tuple

from mas.elements.tools.sandbox_exec.ports import VmSandboxManagerPort
from .ssh_client import SshClient

logger = logging.getLogger(__name__)


class VmSandboxManager(VmSandboxManagerPort):
    """Implements VM sandbox operations over SSH using Podman."""

    def __init__(self) -> None:
        self._clients: Dict[Tuple[str, int, str], SshClient] = {}

    def _get_client(
        self, host: str, port: int, username: str, password: str,
    ) -> SshClient:
        key = (host, port, username)
        client = self._clients.get(key)
        if client is None:
            client = SshClient(host, port, username, password)
            self._clients[key] = client
        return client

    # ── Port implementation ─────────────────────────────────────

    def validate_connectivity(
        self, host: str, port: int, username: str, password: str,
    ) -> bool:
        try:
            client = self._get_client(host, port, username, password)
            client.ensure_connected()
            return True
        except Exception:
            logger.debug(
                "Connectivity check failed for %s:%s", host, port, exc_info=True,
            )
            return False

    def is_alive(
        self, host: str, port: int, username: str, password: str,
    ) -> bool:
        client = self._clients.get((host, port, username))
        if client is None:
            return False
        return client._is_alive()

    def run_command(
        self, host: str, port: int, username: str, password: str, cmd: str,
    ) -> Tuple[int, str, str]:
        client = self._get_client(host, port, username, password)
        return client.exec_command(cmd)

    def setup_bare_repo(
        self,
        host: str, port: int, username: str, password: str,
        bare_repo_path: str,
        git_repo_url: str,
        git_token: str,
    ) -> None:
        client = self._get_client(host, port, username, password)

        exit_code, _, _ = client.exec_command(f"test -d {bare_repo_path}")
        if exit_code == 0:
            logger.info("Bare repo already exists at %s", bare_repo_path)
            return

        if git_token:
            clone_url = git_repo_url.replace(
                "https://", f"https://token:{git_token}@",
            )
        else:
            clone_url = git_repo_url

        exit_code, out, err = client.exec_command(
            f"git clone --bare {shlex.quote(clone_url)} {bare_repo_path}",
        )
        if exit_code != 0:
            raise RuntimeError(
                f"git clone --bare failed (exit {exit_code}): {err or out}"
            )
        logger.info("Cloned bare repo to %s", bare_repo_path)

    def create_worktree(
        self,
        host: str, port: int, username: str, password: str,
        bare_repo_path: str,
        worktree_path: str,
        branch: str,
    ) -> None:
        client = self._get_client(host, port, username, password)

        exit_code, _, _ = client.exec_command(f"test -d {worktree_path}")
        if exit_code == 0:
            logger.info("Worktree already exists at %s", worktree_path)
            return

        exit_code, out, err = client.exec_command(
            f"cd {bare_repo_path} && "
            f"git worktree add {shlex.quote(worktree_path)} "
            f"-b {shlex.quote(branch)} HEAD",
        )
        if exit_code != 0:
            logger.warning(
                "git worktree add failed, falling back to mkdir: %s", err or out,
            )
            client.exec_command(f"mkdir -p {worktree_path}")

        logger.info("Worktree ready at %s", worktree_path)

    def provision_container(
        self,
        host: str, port: int, username: str, password: str,
        container_name: str,
        host_workspace_path: str,
        container_mount_path: str,
        image: str,
        timeout: int,
        network: str,
    ) -> None:
        client = self._get_client(host, port, username, password)
        cmd = (
            f"podman run -d"
            f" --name {container_name}"
            f" --timeout {timeout}"
            f" --network={network}"
            f" -v {host_workspace_path}:{container_mount_path}:Z"
            f" -w {container_mount_path}"
            f" {image}"
            f" sleep infinity"
        )
        exit_code, out, err = client.exec_command(cmd)
        if exit_code != 0:
            raise RuntimeError(
                f"podman run failed (exit {exit_code}): {err or out}"
            )
        logger.info("Container %s started (image: %s)", container_name, image)

    def teardown_container(
        self,
        host: str, port: int, username: str, password: str,
        container_name: str,
    ) -> None:
        client = self._get_client(host, port, username, password)
        client.exec_command(f"podman rm -f {container_name} 2>/dev/null || true")
        logger.debug("Teardown container %s (idempotent)", container_name)

    def execute_in_container(
        self,
        host: str, port: int, username: str, password: str,
        container_name: str,
        cmd: str,
        workdir: str,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        client = self._get_client(host, port, username, password)
        podman_cmd = (
            f"podman exec {container_name} bash -c "
            f"\"cd {workdir} && {cmd}\""
        )

        if stream_callback is not None:
            _, output = client.exec_command_streaming(podman_cmd, stream_callback)
            return output

        exit_code, out, err = client.exec_command(podman_cmd)
        if exit_code != 0:
            return f"{out}\nSTDERR:\n{err}".strip() if err else out
        return out
