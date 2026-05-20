from typing import Literal
from pydantic import Field
from mas.elements.tools.common.base_config import BaseToolConfig
from mas.core.field_hints import SecretHint
from .identifiers import Identifier


class SandboxExecToolConfig(BaseToolConfig):
    """Configuration for the VM Sandbox Exec tool."""

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
        description="Working directory on the VM",
    )

    git_repo_url: str = Field(
        "",
        description="Git repository URL to clone (leave empty to skip)",
    )
    git_token: str = Field(
        "",
        description="Git access token for private repos",
        json_schema_extra=SecretHint(
            reason="Git token should be masked",
            allow_reveal=False,
        ).to_hints(),
    )
