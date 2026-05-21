from __future__ import annotations

from typing import Any, TYPE_CHECKING
from pydantic import BaseModel, Field
from mas.elements.tools.common.base_tool import BaseTool
from mas.core.sandbox.ports import VmConnectionInfo

if TYPE_CHECKING:
    from mas.core.sandbox.ports import VmSandboxManagerPort


class SandboxExecInput(BaseModel):
    """Input schema for sandbox command execution."""

    cmd: str = Field(
        ..., description="Shell command to run inside the container"
    )
    workdir: str = Field(
        "",
        description="Working directory inside the container",
    )


class SandboxExecTool(BaseTool):
    """Execute commands in an isolated VM container via a sandbox manager."""

    name: str = "SandboxExecTool"
    description: str = (
        "Execute a shell command inside an isolated container on a VM"
    )
    args_schema = SandboxExecInput

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        workspace_path: str,
        sandbox_manager: VmSandboxManagerPort,
        execution_ctx: Any = None,
    ) -> None:
        super().__init__()
        self._conn = VmConnectionInfo(
            host=host,
            port=port,
            username=username,
            password=password,
        )
        self._workspace_path = workspace_path
        self._sandbox_manager = sandbox_manager
        self._execution_ctx = execution_ctx

        translation = str.maketrans(".:- /", "_____")
        safe_host = host.translate(translation)
        self.name = f"sandbox_exec_{safe_host}_{port}"

        self._container_name = f"sandbox_{safe_host}_{port}"

        self.description = (
            f"Run shell commands inside an isolated container "
            f"on {host}:{port}.\n\n"
            f"The tool executes the command in a Podman container "
            f"managed on the remote VM. You only need to specify "
            f"the command — the tool handles the connection, "
            f"container routing, and execution.\n\n"
            f"Connection Details:\n"
            f"• Host: {host}\n"
            f"• Port: {port}\n"
            f"• Workspace: {workspace_path}\n\n"
            f"Usage: Provide the shell command as an argument. "
            f"Optionally specify a working directory inside the "
            f"container."
        )

    def run(self, *args: Any, **kwargs: Any) -> str:
        inp = self.args_schema(**kwargs)
        try:
            return self._sandbox_manager.execute_in_container(
                self._conn,
                self._container_name,
                inp.cmd,
                inp.workdir,
            )
        except Exception as e:
            return (
                f"ERROR: Failed to execute command in container "
                f"'{self._container_name}': {e}"
            )
