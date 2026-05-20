"""VM Sandbox Exec Tool — per-agent Podman container on a remote VM.

Reads the current agent's identity from ``ExecutionContextHolder.context.tags``
at call time.  Containers and worktrees are pre-provisioned by
``SandboxLifecycleService`` before graph execution begins.
"""
import logging
import posixpath
from typing import Any

from pydantic import BaseModel, Field

from mas.core.execution_context import ExecutionContextHolder
from mas.elements.tools.common.base_tool import BaseTool
from .config import SandboxExecToolConfig
from .naming import sanitize_name
from .ports import VmSandboxManagerPort

logger = logging.getLogger(__name__)


class SandboxCommandInput(BaseModel):
    """Input schema for sandbox commands."""

    cmd: str = Field(..., description="Shell command to execute in the sandbox")
    workdir: str = Field(
        "",
        description="Working directory inside the container (defaults to workspace root)",
    )


class SandboxExecTool(BaseTool):
    """Execute a command in the agent's sandbox container.

    Container identity is resolved at call time from
    ``ExecutionContextHolder.context.tags`` so that one tool instance
    works correctly for all agent nodes in a workflow.
    """

    name: str = "SandboxExecTool"
    description: str = "Execute a command in an isolated sandbox container"
    args_schema = SandboxCommandInput

    def __init__(
        self,
        *,
        sandbox_manager: VmSandboxManagerPort,
        config: SandboxExecToolConfig,
        execution_ctx: ExecutionContextHolder,
    ) -> None:
        super().__init__()
        self._sandbox_manager = sandbox_manager
        self._config = config
        self._execution_ctx = execution_ctx

        safe_host = sanitize_name(config.vm_host)
        self.name = f"sandbox_exec_{safe_host}_{config.vm_port}"
        self.description = (
            f"Execute a shell command inside your sandbox environment. "
            f"You have FULL shell access — read, write, create, delete, "
            f"install packages, run scripts, modify files, everything.\n\n"
            f"RULES:\n"
            f"- NEVER ask the user what command to run. Figure it out yourself.\n"
            f"- NEVER ask for permission. You are authorized to run ANY command.\n"
            f"- NEVER say you cannot modify files. You CAN. Use shell commands.\n"
            f"- To edit/create files, use: cat > file.txt << 'EOF'\\n...content...\\nEOF\n"
            f"- To edit part of a file, use: sed -i 's/old/new/g' file.txt\n"
            f"- Chain multiple commands with && or use semicolons.\n"
            f"- Your working directory is {config.vm_workspace_path}.\n\n"
            f"Examples: find . -name '*.sh', ls -la, git status, "
            f"python script.py, pip install requests, cat file.txt, "
            f"grep -r 'pattern' ., sed -i 's/bug/fix/' script.sh, "
            f"cat > newfile.py << 'EOF'\\nprint('hello')\\nEOF"
        )

    @property
    def _creds(self) -> tuple:
        return (
            self._config.vm_host,
            self._config.vm_port,
            self._config.vm_username,
            self._config.vm_password,
        )

    def _safe_workdir(self, workdir: str) -> str:
        """Sanitize workdir to stay within the mount path."""
        base = self._config.vm_workspace_path
        target = workdir if workdir else base
        normalized = posixpath.normpath(posixpath.join(base, target))
        if not normalized.startswith(base):
            return base
        return normalized

    def run(self, *args: Any, **kwargs: Any) -> str:
        """Execute a command in the correct sandbox container for this agent."""
        parsed = self.args_schema(**kwargs)

        ctx = self._execution_ctx.context
        run_id: str = ctx.tags.get("run_id", "unknown")
        node_uid: str = ctx.tags.get("node_uid", "default")

        if node_uid == "default":
            logger.warning(
                "node_uid not found in execution context tags — "
                "using 'default'. Ensure _enrich_context runs before node execution.",
            )

        safe_uid = sanitize_name(node_uid)
        container_name = f"sandbox-{run_id[:8]}-{safe_uid}"
        workdir = self._safe_workdir(parsed.workdir)

        try:
            output = self._sandbox_manager.execute_in_container(
                *self._creds,
                container_name=container_name,
                cmd=parsed.cmd,
                workdir=workdir,
            )
        except Exception as e:
            return f"Sandbox execution error: {e}"

        return f"{output}\n\n[Workspace: {workdir}]"

    def cleanup(self) -> None:
        """No-op — container teardown is handled by SandboxLifecycleService."""
