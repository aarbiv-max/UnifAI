"""Application-layer orchestration of sandbox lifecycle.

Coordinates bare repo setup, per-agent worktree creation, container
provisioning, and teardown.  Depends only on ``VmSandboxManagerPort``.
"""
import logging
from typing import Dict, List

from .config import SandboxExecToolConfig
from .models import SandboxContainerInfo, SandboxState
from .naming import sanitize_name
from .ports import VmSandboxManagerPort

logger = logging.getLogger(__name__)

_DEFAULT_IMAGE = "python:3.11-slim"
_CONTAINER_TIMEOUT = 7200
_CONTAINER_NETWORK = "slirp4netns"


class SandboxLifecycleService:
    """Manages the full lifecycle of sandbox containers for a workflow session."""

    def __init__(self, sandbox_manager: VmSandboxManagerPort) -> None:
        self._manager = sandbox_manager

    def provision_for_session(
        self,
        run_id: str,
        agent_ids: List[str],
        config: SandboxExecToolConfig,
    ) -> SandboxState:
        """Provision bare repo + one container per agent.  Idempotent.

        Args:
            run_id: Session/workflow identifier.
            agent_ids: Graph node UIDs that need sandbox containers.
            config: VM credentials and git repo from the tool resource.

        Returns:
            Populated ``SandboxState`` with all container info.
        """
        creds = (config.vm_host, config.vm_port, config.vm_username, config.vm_password)
        workspace = config.vm_workspace_path

        self._manager.run_command(*creds, f"mkdir -p {workspace}")

        bare_repo_path = f"{workspace}/repo.git"
        if config.git_repo_url:
            self._manager.setup_bare_repo(
                *creds,
                bare_repo_path=bare_repo_path,
                git_repo_url=config.git_repo_url,
                git_token=config.git_token,
            )

        containers: Dict[str, SandboxContainerInfo] = {}
        for agent_id in agent_ids:
            safe_id = sanitize_name(agent_id)
            container_name = f"sandbox-{run_id[:8]}-{safe_id}"
            worktree_path = f"{workspace}/wt-{safe_id}"
            branch_name = f"sandbox/{safe_id}"

            if config.git_repo_url:
                self._manager.create_worktree(
                    *creds,
                    bare_repo_path=bare_repo_path,
                    worktree_path=worktree_path,
                    branch=branch_name,
                )
            else:
                self._manager.run_command(*creds, f"mkdir -p {worktree_path}")

            self._manager.teardown_container(*creds, container_name)
            self._manager.provision_container(
                *creds,
                container_name=container_name,
                host_workspace_path=worktree_path,
                container_mount_path=config.vm_workspace_path,
                image=_DEFAULT_IMAGE,
                timeout=_CONTAINER_TIMEOUT,
                network=_CONTAINER_NETWORK,
            )

            containers[agent_id] = SandboxContainerInfo(
                agent_id=agent_id,
                container_name=container_name,
                worktree_path=worktree_path,
                status="ready",
            )
            logger.info(
                "Provisioned sandbox for agent %s: container=%s worktree=%s",
                agent_id, container_name, worktree_path,
            )

        return SandboxState(
            session_id=run_id,
            vm_host=config.vm_host,
            containers=containers,
        )

    def teardown_for_session(
        self,
        sandbox_state: SandboxState,
        config: SandboxExecToolConfig,
    ) -> None:
        """Delete all containers tracked in *sandbox_state*.  Does NOT delete worktrees."""
        creds = (config.vm_host, config.vm_port, config.vm_username, config.vm_password)
        for info in sandbox_state.containers.values():
            try:
                self._manager.teardown_container(*creds, info.container_name)
            except Exception:
                logger.exception("Failed to tear down container %s", info.container_name)

    def teardown_by_naming(
        self,
        run_id: str,
        agent_ids: List[str],
        config: SandboxExecToolConfig,
    ) -> None:
        """Fallback teardown using deterministic naming (crash recovery)."""
        creds = (config.vm_host, config.vm_port, config.vm_username, config.vm_password)
        for agent_id in agent_ids:
            container_name = f"sandbox-{run_id[:8]}-{sanitize_name(agent_id)}"
            try:
                self._manager.teardown_container(*creds, container_name)
            except Exception:
                logger.exception(
                    "Failed to tear down container %s (naming fallback)", container_name,
                )
