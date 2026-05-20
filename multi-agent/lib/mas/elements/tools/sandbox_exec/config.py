from typing import Literal
from pydantic import Field
from mas.elements.tools.common.base_config import BaseToolConfig
from mas.core.field_hints import SecretHint
from .identifiers import Identifier


class SandboxExecToolConfig(BaseToolConfig):
    """Configuration for the VM Sandbox Exec tool.

    Connects to a remote VM via SSH, creates per-agent git worktrees
    for code isolation, and runs Podman containers per agent.
    """

    type: Literal[Identifier.TYPE] = Identifier.TYPE

    vm_host: str = Field(..., description="IP or hostname of the target VM")
    vm_port: int = Field(22, description="SSH port")
    vm_username: str = Field(..., description="SSH user name")
    vm_password: str = Field(
        ...,
        description="SSH password",
        json_schema_extra=SecretHint(
            reason="Password credential should be masked",
            allow_reveal=False,
        ).to_hints(),
    )

    vm_workspace_path: str = Field(
        "/opt/sandbox",
        description=(
            "Stable directory root for worktrees on the VM. "
            "Persists across sessions — does NOT contain run_id."
        ),
    )

    git_repo_url: str = Field(
        "",
        description="Git repository URL to clone. Leave empty for plain directories.",
    )
    git_branch: str = Field("main", description="Branch to check out in worktrees")
    git_token: str = Field(
        "",
        description="Git access token (for private repos)",
        json_schema_extra=SecretHint(
            reason="Git token should be masked",
            allow_reveal=False,
        ).to_hints(),
    )

    vm_container_image: str = Field(
        "python:3.11-slim",
        description="Podman container image for agent sandboxes",
    )
    container_timeout: int = Field(
        7200,
        description="Container TTL in seconds (safety net, default 2h)",
    )
    container_network: str = Field(
        "none",
        description="Podman --network flag (default: isolated, no network)",
    )
