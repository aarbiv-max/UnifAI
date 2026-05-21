from typing import Literal
from pydantic import Field
from mas.elements.tools.common.base_config import BaseToolConfig
from mas.core.field_hints import SecretHint
from .identifiers import Identifier


class SandboxExecToolConfig(BaseToolConfig):
    """Configuration for the sandbox-execution tool."""

    type: Literal[Identifier.TYPE] = Identifier.TYPE
    vm_host: str = Field(
        ..., description="IP or DNS name of the target VM"
    )
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
        description="Workspace directory on the VM",
    )
    git_repo_url: str = Field(
        "", description="Git repository URL to clone"
    )
    git_token: str = Field(
        "",
        description="Git access token",
        json_schema_extra=SecretHint(
            reason="Token credential should be masked",
            allow_reveal=False,
        ).to_hints(),
    )
