"""Port (interface) for sandbox infrastructure operations.

Adapters implement this to provide the actual OpenShift (or other)
sandbox management.  The port is stateless — all cluster/auth info
is passed per-call so the adapter needs no mutable state.
"""
from abc import ABC, abstractmethod
from typing import Optional


class SandboxManagerPort(ABC):
    """Infrastructure port for sandbox pod and PVC operations."""

    @abstractmethod
    def provision_pvc(
        self,
        pvc_name: str,
        namespace: str,
        cluster_api: str,
        token: str,
        skip_tls_verify: bool = False,
    ) -> None:
        """Create a 2Gi RWX PVC if it doesn't already exist (idempotent)."""
        ...

    @abstractmethod
    def provision_pod(
        self,
        pod_name: str,
        pvc_name: str,
        namespace: str,
        cluster_api: str,
        token: str,
        git_repo_url: str,
        worktree_path: str,
        branch_name: str,
        git_token: str = "",
        skip_tls_verify: bool = False,
    ) -> None:
        """Create a sandbox pod, mount PVC, and set up a git worktree (idempotent)."""
        ...

    @abstractmethod
    def execute(
        self,
        pod_name: str,
        namespace: str,
        cluster_api: str,
        token: str,
        cmd: str,
        workdir: Optional[str] = None,
        skip_tls_verify: bool = False,
    ) -> str:
        """Exec a command inside a running pod.  Returns combined stdout/stderr."""
        ...

    @abstractmethod
    def teardown_pod(
        self,
        pod_name: str,
        namespace: str,
        cluster_api: str,
        token: str,
        skip_tls_verify: bool = False,
    ) -> None:
        """Delete a single pod (idempotent — ignores not-found)."""
        ...

    @abstractmethod
    def is_pod_alive(
        self,
        pod_name: str,
        namespace: str,
        cluster_api: str,
        token: str,
        skip_tls_verify: bool = False,
    ) -> bool:
        """Return True if the pod phase is Running."""
        ...
