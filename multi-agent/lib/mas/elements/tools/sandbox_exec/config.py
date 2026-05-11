from typing import Literal

from pydantic import Field

from mas.core.field_hints import SecretHint
from mas.elements.tools.common.base_config import BaseToolConfig
from .identifiers import Identifier


class SandboxExecToolConfig(BaseToolConfig):
    """Configuration for the sandbox code-execution tool.

    Users fill this in when adding the tool resource via the UI.
    Secrets are masked in the catalog form via SecretHint.
    """

    type: Literal[Identifier.TYPE] = Identifier.TYPE

    cluster_api: str = Field(
        ...,
        description="OpenShift API server URL (e.g. https://api.cluster.example.com:6443)",
        json_schema_extra=SecretHint(
            reason="Cluster endpoint should be treated as sensitive",
            allow_reveal=True,
        ).to_hints(),
    )

    cluster_token: str = Field(
        ...,
        description="OpenShift authentication token",
        json_schema_extra=SecretHint(
            reason="Token credential should be masked",
            allow_reveal=False,
        ).to_hints(),
    )

    namespace: str = Field(
        ...,
        description="Target namespace for sandbox pods and PVC",
    )

    git_repo_url: str = Field(
        ...,
        description="Git repository URL to clone into the sandbox workspace",
    )

    git_token: str = Field(
        default="",
        description="Personal access token for private repo authentication (leave empty for public repos)",
        json_schema_extra=SecretHint(
            reason="Git token should be masked",
            allow_reveal=False,
        ).to_hints(),
    )

    skip_tls_verify: bool = Field(
        default=False,
        description="Skip TLS certificate verification for the OpenShift cluster",
    )
