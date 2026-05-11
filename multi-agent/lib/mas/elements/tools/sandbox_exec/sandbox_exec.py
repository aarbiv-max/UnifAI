"""Sandbox Exec tool — LLM-callable command execution inside a sandbox pod."""
from typing import Any, Optional

from pydantic import BaseModel, Field

from mas.core.execution_context import ExecutionContextHolder
from mas.elements.tools.common.base_tool import BaseTool
from .config import SandboxExecToolConfig
from .ports import SandboxManagerPort


class SandboxCommandInput(BaseModel):
    """Input schema for sandbox commands."""

    cmd: str = Field(..., description="Shell command to execute in the sandbox")
    workdir: Optional[str] = Field(
        None, description="Working directory override (defaults to the agent's worktree)"
    )


class SandboxExecTool(BaseTool):
    """Execute a command in the agent's sandbox pod.

    Pod identity is resolved **at call time** from ``ExecutionContext.tags``
    so that one tool instance works correctly for all agent nodes.
    """

    name: str = "sandbox_exec"
    description: str = (
        "Execute a shell command in the sandbox pod. "
        "The sandbox is an isolated container with your git workspace mounted."
    )
    args_schema = SandboxCommandInput

    def __init__(
        self,
        *,
        sandbox_manager: SandboxManagerPort,
        config: SandboxExecToolConfig,
        execution_ctx: ExecutionContextHolder,
    ) -> None:
        super().__init__()
        self._sandbox_manager = sandbox_manager
        self._config = config
        self._execution_ctx = execution_ctx

    def run(self, *args: Any, **kwargs: Any) -> str:
        """Execute a command in the correct sandbox pod for this agent."""
        parsed = self.args_schema(**kwargs)

        ctx = self._execution_ctx.context
        run_id: str = ctx.tags["run_id"]
        node_uid: str = ctx.tags["node_uid"]

        pod_name = f"sandbox-{run_id[:8]}-{node_uid}"
        workdir = parsed.workdir or f"/workspace/worktree-{node_uid}"

        try:
            return self._sandbox_manager.execute(
                pod_name=pod_name,
                namespace=self._config.namespace,
                cluster_api=self._config.cluster_api,
                token=self._config.cluster_token,
                cmd=parsed.cmd,
                workdir=workdir,
                skip_tls_verify=self._config.skip_tls_verify,
            )
        except Exception as e:
            return f"Sandbox execution error: {e}"
