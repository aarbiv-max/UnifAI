from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class VmConnectionInfo:
    """Immutable value object for VM target + credentials."""

    host: str
    port: int
    username: str
    password: str


class VmSandboxManagerPort(ABC):
    """Abstract contract for VM sandbox operations.

    Every method receives a ``VmConnectionInfo`` so adapters stay
    stateless with respect to *which* VM they target — the caller
    decides.
    """

    @abstractmethod
    def validate_connectivity(
        self, conn: VmConnectionInfo, timeout: float = 10.0,
    ) -> bool:
        """Return True if the VM is reachable over SSH within *timeout* seconds."""
        ...

    @abstractmethod
    def is_alive(self, conn: VmConnectionInfo) -> bool:
        """Quick liveness check (cached transport if available)."""
        ...

    @abstractmethod
    def run_command(
        self, conn: VmConnectionInfo, cmd: str,
    ) -> Tuple[int, str, str]:
        """Execute *cmd* on the VM and return (exit_code, stdout, stderr)."""
        ...

    @abstractmethod
    def setup_bare_repo(
        self,
        conn: VmConnectionInfo,
        workspace_path: str,
        git_url: str,
        git_token: str = "",
    ) -> str:
        """Clone/fetch into a bare repo under *workspace_path* and return its path."""
        ...

    @abstractmethod
    def create_worktree(
        self,
        conn: VmConnectionInfo,
        workspace_path: str,
        agent_id: str,
    ) -> str:
        """Create a git worktree for *agent_id* and return its path."""
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    def teardown_container(
        self,
        conn: VmConnectionInfo,
        container_name: str,
    ) -> None:
        """Stop and remove the container."""
        ...

    @abstractmethod
    def execute_in_container(
        self,
        conn: VmConnectionInfo,
        container_name: str,
        cmd: str,
        workdir: str = "",
    ) -> str:
        """Run *cmd* inside an existing container and return combined output."""
        ...

    @abstractmethod
    def write_file(
        self,
        conn: VmConnectionInfo,
        worktree_path: str,
        relative_path: str,
        content: str,
    ) -> None:
        """Write *content* to a file in the worktree via SFTP."""
        ...

    @abstractmethod
    def read_file(
        self,
        conn: VmConnectionInfo,
        worktree_path: str,
        relative_path: str,
    ) -> str:
        """Read a file from the worktree and return its content."""
        ...
