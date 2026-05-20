"""VM Sandbox Exec Tool — per-agent isolated Podman containers.

Each agent gets its own git worktree mounted into a dedicated container.
Caller identity is resolved via contextvars (thread-safe, no shared state).
Workspaces persist across sessions; only containers are ephemeral.
"""
import logging
import posixpath
import re
import threading
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from mas.elements.tools.common.base_tool import BaseTool
from mas.elements.tools.common.execution.context import caller_uid_var
from .config import SandboxExecToolConfig
from .ports import VmSandboxManagerPort

logger = logging.getLogger(__name__)

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9\-]")


def _sanitize_name(raw: str) -> str:
    """Replace non-alphanumeric characters (except hyphens) with hyphens."""
    return _SAFE_NAME_RE.sub("-", raw).strip("-") or "default"


class SandboxCommandInput(BaseModel):
    cmd: str = Field(..., description="Shell command to run inside the sandbox")
    workdir: str = Field(
        "/workspace",
        description="Working directory inside the container (must be under /workspace)",
    )


class SandboxExecTool(BaseTool):
    """Execute commands in per-agent Podman containers on a remote VM."""

    name: str = "SandboxExecTool"
    description: str = "Execute a command in an isolated sandbox container"
    args_schema = SandboxCommandInput

    def __init__(
        self,
        *,
        config: SandboxExecToolConfig,
        vm_sandbox_manager: VmSandboxManagerPort,
        run_id: str,
    ) -> None:
        super().__init__()
        self._cfg = config
        self._vm = vm_sandbox_manager
        self._run_id = run_id

        self._provisioned: Dict[str, str] = {}
        self._bare_repo_ready = False
        self._lock = threading.Lock()

        safe_host = _sanitize_name(config.vm_host)
        self.name = f"sandbox_exec_{safe_host}_{config.vm_port}"
        self.description = (
            f"Execute commands in isolated sandbox containers on {config.vm_host}.\n\n"
            f"Each agent gets its own workspace at /workspace backed by a git worktree.\n"
            f"Connection: {config.vm_host}:{config.vm_port} as {config.vm_username}\n"
            f"Image: {config.vm_container_image}\n"
            f"Workspace: {config.vm_workspace_path}"
        )

    # ── SSH credential shorthand ────────────────────────────────

    @property
    def _creds(self) -> tuple:
        return (
            self._cfg.vm_host,
            self._cfg.vm_port,
            self._cfg.vm_username,
            self._cfg.vm_password,
        )

    # ── Lazy provisioning ───────────────────────────────────────

    def _ensure_agent_provisioned(self, agent_uid: str) -> str:
        """Provision a worktree + container for *agent_uid* (idempotent).

        Returns the container name.
        """
        safe_uid = _sanitize_name(agent_uid)
        with self._lock:
            if safe_uid in self._provisioned:
                return self._provisioned[safe_uid]

            workspace_base = self._cfg.vm_workspace_path
            worktree_path = f"{workspace_base}/wt-{safe_uid}"
            container_name = f"sandbox-{self._run_id[:8]}-{safe_uid}"

            self._setup_workspace(workspace_base, worktree_path)
            self._verify_worktree(worktree_path)

            self._vm.teardown_container(*self._creds, container_name)
            self._vm.provision_container(
                *self._creds,
                container_name=container_name,
                host_worktree_path=worktree_path,
                image=self._cfg.vm_container_image,
                timeout=self._cfg.container_timeout,
                network=self._cfg.container_network,
            )

            self._provisioned[safe_uid] = container_name
            logger.info(
                "Provisioned sandbox for agent %s → container %s",
                safe_uid, container_name,
            )
            return container_name

    def _setup_workspace(self, workspace_base: str, worktree_path: str) -> None:
        """Set up bare repo + worktree (or plain directory)."""
        if self._cfg.git_repo_url:
            self._ensure_bare_repo(workspace_base)
            self._ensure_worktree(workspace_base, worktree_path)
        else:
            self._vm.run_command(*self._creds, f"mkdir -p {worktree_path}")

    def _ensure_bare_repo(self, workspace_base: str) -> None:
        if self._bare_repo_ready:
            return
        bare_repo_path = f"{workspace_base}/repo.git"
        self._vm.setup_bare_repo(
            *self._creds,
            bare_repo_path=bare_repo_path,
            git_repo_url=self._cfg.git_repo_url,
            git_token=self._cfg.git_token,
        )
        self._bare_repo_ready = True

    def _ensure_worktree(self, workspace_base: str, worktree_path: str) -> None:
        exit_code, _, _ = self._vm.run_command(
            *self._creds, f"test -d {worktree_path}",
        )
        if exit_code == 0:
            logger.info("Reusing existing worktree at %s", worktree_path)
            return

        bare_repo_path = f"{workspace_base}/repo.git"
        try:
            self._vm.create_worktree(
                *self._creds,
                bare_repo_path=bare_repo_path,
                worktree_path=worktree_path,
                branch=self._cfg.git_branch,
            )
        except Exception:
            logger.warning(
                "git worktree add failed for %s, falling back to mkdir",
                worktree_path, exc_info=True,
            )
            self._vm.run_command(*self._creds, f"mkdir -p {worktree_path}")

    def _verify_worktree(self, worktree_path: str) -> None:
        exit_code, _, _ = self._vm.run_command(
            *self._creds, f"test -d {worktree_path}",
        )
        if exit_code != 0:
            raise RuntimeError(
                f"Worktree directory does not exist after setup: {worktree_path}"
            )

    # ── Workdir sanitization ────────────────────────────────────

    @staticmethod
    def _safe_workdir(workdir: str) -> str:
        normalized = posixpath.normpath(posixpath.join("/workspace", workdir))
        if not normalized.startswith("/workspace"):
            return "/workspace"
        return normalized

    # ── Tool execution ──────────────────────────────────────────

    def run(self, *args: Any, **kwargs: Any) -> str:
        inp = self.args_schema(**kwargs)
        caller_uid = caller_uid_var.get()
        if not caller_uid:
            logger.warning("caller_uid_var is empty — using 'default'")
            caller_uid = "default"

        container_name = self._ensure_agent_provisioned(caller_uid)
        safe_workdir = self._safe_workdir(inp.workdir)

        output = self._vm.execute_in_container(
            *self._creds,
            container_name=container_name,
            cmd=inp.cmd,
            workdir=safe_workdir,
        )
        return f"{output}\n\n[Workspace: {safe_workdir}]"

    # ── Cleanup (containers only — filesystem persists) ─────────

    def cleanup(self) -> None:
        """Tear down all containers provisioned by this tool instance."""
        for agent_uid, container_name in self._provisioned.items():
            try:
                self._vm.teardown_container(*self._creds, container_name)
                logger.info("Cleaned up container %s", container_name)
            except Exception:
                logger.warning(
                    "Failed to teardown container %s for agent %s",
                    container_name, agent_uid, exc_info=True,
                )
        self._provisioned.clear()
