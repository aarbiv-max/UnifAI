"""Port (interface) for VM sandbox management.

Defines the abstract contract that adapters must implement.
No infrastructure dependencies — pure interface.
"""
from abc import ABC, abstractmethod
from typing import Callable, Optional, Tuple


class VmSandboxManagerPort(ABC):
    """Abstract interface for managing VM-based sandbox environments."""

    @abstractmethod
    def validate_connectivity(
        self, host: str, port: int, username: str, password: str,
    ) -> bool:
        """Check SSH connectivity to the VM. Returns True on success."""
        ...

    @abstractmethod
    def is_alive(
        self, host: str, port: int, username: str, password: str,
    ) -> bool:
        """Lightweight liveness check (no full reconnect)."""
        ...

    @abstractmethod
    def run_command(
        self, host: str, port: int, username: str, password: str, cmd: str,
    ) -> Tuple[int, str, str]:
        """Execute a raw SSH command. Returns (exit_code, stdout, stderr)."""
        ...

    @abstractmethod
    def setup_bare_repo(
        self,
        host: str, port: int, username: str, password: str,
        bare_repo_path: str,
        git_repo_url: str,
        git_token: str,
    ) -> None:
        """Clone a bare git repository (idempotent — skips if exists)."""
        ...

    @abstractmethod
    def create_worktree(
        self,
        host: str, port: int, username: str, password: str,
        bare_repo_path: str,
        worktree_path: str,
        branch: str,
    ) -> None:
        """Create a git worktree from the bare repo."""
        ...

    @abstractmethod
    def provision_container(
        self,
        host: str, port: int, username: str, password: str,
        container_name: str,
        host_worktree_path: str,
        image: str,
        timeout: int,
        network: str,
    ) -> None:
        """Start a Podman container with the worktree mounted at /workspace."""
        ...

    @abstractmethod
    def teardown_container(
        self,
        host: str, port: int, username: str, password: str,
        container_name: str,
    ) -> None:
        """Force-remove a container (idempotent)."""
        ...

    @abstractmethod
    def execute_in_container(
        self,
        host: str, port: int, username: str, password: str,
        container_name: str,
        cmd: str,
        workdir: str,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Execute a command inside a running container. Returns stdout."""
        ...
