from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

from mas.elements.tools.common.base_tool import BaseTool
from mas.core.sandbox.ports import VmConnectionInfo

if TYPE_CHECKING:
    from mas.core.sandbox.ports import VmSandboxManagerPort

_CONTAINER_NAME_SANITIZE = str.maketrans(".:- /", "_____")


class SandboxExecInput(BaseModel):
    """Input schema for the multi-action sandbox tool."""

    action: Literal[
        "exec", "write_file", "read_file", "list_files",
    ] = Field(
        "exec",
        description=(
            "Action to perform. "
            "'exec' runs a command inside the container (requires 'cmd'). "
            "'write_file' writes content to a file (requires 'path' and 'content'). "
            "'read_file' reads a file and returns its content (requires 'path'). "
            "'list_files' lists files in the workspace, optionally filtered by "
            "a glob pattern (optional 'path' as glob, e.g. '*.sh' or 'src/**/*.py')."
        ),
    )
    cmd: str = Field("", description="Command to run (for action='exec')")
    path: str = Field(
        "",
        description=(
            "File path relative to /workspace (for read_file, write_file), "
            "or glob pattern (for list_files, e.g. '*.sh')"
        ),
    )
    content: str = Field(
        "", description="File content (for action='write_file')"
    )


@dataclass
class AgentSandboxState:
    """Per-agent sandbox state held by the parent tool."""

    worktree_path: str = ""
    container_name: str = ""
    worktree_ready: bool = False
    container_ready: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)


class SandboxExecTool(BaseTool):
    """Shared sandbox tool that produces per-agent proxies.

    Registered once in ``SessionRegistry``; each agent receives a
    lightweight ``_SandboxAgentProxy`` via ``scoped_for_agent()``.
    """

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

        safe_host = host.translate(_CONTAINER_NAME_SANITIZE)
        self.name = f"sandbox_exec_{safe_host}_{port}"

        self.description = (
            f"Interact with an isolated sandbox environment on "
            f"{host}:{port}.\n\n"
            f"Supports four actions:\n"
            f"• action='list_files': List files in the workspace. "
            f"Optionally pass 'path' as a glob pattern "
            f"(e.g. '*.sh', 'src/**/*.py'). No pattern lists everything.\n"
            f"• action='read_file': Read a file from /workspace "
            f"(requires 'path', e.g. 'src/main.py').\n"
            f"• action='write_file': Write content to a file in "
            f"/workspace (requires 'path' and 'content').\n"
            f"• action='exec': Run a shell command in the container "
            f"(requires 'cmd'). Use for running code, tests, installs.\n\n"
            f"Start with list_files to discover the repo structure, "
            f"then read_file to inspect code. Use exec only when you "
            f"need to run something."
        )

        self._agent_states: Dict[str, AgentSandboxState] = {}

    def scoped_for_agent(self, agent_uid: str) -> BaseTool:
        """Return a per-agent proxy backed by shared state."""
        if agent_uid not in self._agent_states:
            self._agent_states[agent_uid] = AgentSandboxState()
        return _SandboxAgentProxy(parent=self, agent_uid=agent_uid)

    def run(self, *args: Any, **kwargs: Any) -> str:
        return (
            "ERROR: SandboxExecTool must be scoped to an agent via "
            "scoped_for_agent() before use."
        )


class _SandboxAgentProxy(BaseTool):
    """Lightweight per-agent proxy delegating to a shared SandboxExecTool."""

    name: str = "sandbox_proxy"
    description: str = ""
    args_schema = SandboxExecInput

    def __init__(
        self, parent: SandboxExecTool, agent_uid: str,
    ) -> None:
        super().__init__()
        self._parent = parent
        self._agent_uid = agent_uid
        self.name = parent.name
        self.description = parent.description

    def run(self, *args: Any, **kwargs: Any) -> str:
        inp = self.args_schema(**kwargs)

        if inp.action == "exec" and not inp.cmd:
            return "ERROR: 'cmd' is required for action='exec'"
        if inp.action == "write_file" and (not inp.path or not inp.content):
            return (
                "ERROR: 'path' and 'content' are required "
                "for action='write_file'"
            )
        if inp.action == "read_file" and not inp.path:
            return "ERROR: 'path' is required for action='read_file'"

        state = self._parent._agent_states[self._agent_uid]
        self._ensure_worktree(state)

        try:
            if inp.action == "list_files":
                return self._list_files(state, inp.path)
            elif inp.action == "read_file":
                return self._parent._sandbox_manager.read_file(
                    self._parent._conn,
                    state.worktree_path,
                    inp.path,
                )
            elif inp.action == "write_file":
                self._parent._sandbox_manager.write_file(
                    self._parent._conn,
                    state.worktree_path,
                    inp.path,
                    inp.content,
                )
                return f"File written: {inp.path}"
            elif inp.action == "exec":
                self._ensure_container(state)
                return self._exec_with_recovery(state, inp.cmd)
        except Exception as exc:
            return f"ERROR: {exc}"
        return "ERROR: unknown action"

    # ------------------------------------------------------------------

    def _list_files(
        self, state: AgentSandboxState, pattern: str,
    ) -> str:
        """List files in the worktree via SSH (no container needed)."""
        import shlex

        wt = shlex.quote(state.worktree_path)
        if pattern:
            cmd = f"find {wt} -name {shlex.quote(pattern)} -type f | sort"
        else:
            cmd = (
                f"find {wt} -type f "
                f"-not -path '*/.git/*' | sort"
            )
        exit_code, stdout, stderr = (
            self._parent._sandbox_manager.run_command(
                self._parent._conn, cmd,
            )
        )
        if exit_code != 0:
            return f"ERROR: {stderr}"
        prefix = state.worktree_path.rstrip("/") + "/"
        lines = stdout.strip().splitlines()
        relative = [
            ln[len(prefix):] if ln.startswith(prefix) else ln
            for ln in lines
        ]
        return "\n".join(relative) if relative else "(no files found)"

    def _ensure_worktree(self, state: AgentSandboxState) -> None:
        """Create the worktree on first call (any action)."""
        if state.worktree_ready:
            return
        with state.lock:
            if state.worktree_ready:
                return
            state.worktree_path = (
                self._parent._sandbox_manager.create_worktree(
                    self._parent._conn,
                    self._parent._workspace_path,
                    self._agent_uid,
                )
            )
            safe_uid = self._agent_uid.translate(_CONTAINER_NAME_SANITIZE)
            state.container_name = f"sandbox-{safe_uid}"
            state.worktree_ready = True

    def _ensure_container(self, state: AgentSandboxState) -> None:
        """Provision the container on first exec call."""
        if state.container_ready:
            return
        with state.lock:
            if state.container_ready:
                return
            self._parent._sandbox_manager.provision_container(
                self._parent._conn,
                state.container_name,
                state.worktree_path,
                "/workspace",
            )
            state.container_ready = True

    def _exec_with_recovery(
        self, state: AgentSandboxState, cmd: str,
    ) -> str:
        """Execute in container; re-provision once on failure."""
        try:
            return self._parent._sandbox_manager.execute_in_container(
                self._parent._conn,
                state.container_name,
                cmd,
                "/workspace",
            )
        except RuntimeError:
            self._parent._sandbox_manager.provision_container(
                self._parent._conn,
                state.container_name,
                state.worktree_path,
                "/workspace",
            )
            return self._parent._sandbox_manager.execute_in_container(
                self._parent._conn,
                state.container_name,
                cmd,
                "/workspace",
            )
