from enum import Enum
from dataclasses import dataclass
from typing import List


class Identifier(str, Enum):
    """Machine-readable key for the Sandbox Exec tool."""
    TYPE = "sandbox_exec"


@dataclass(frozen=True)
class Meta:
    name: str
    description: str
    tags: List[str]


META = Meta(
    name="VM Sandbox Exec",
    description=(
        "Execute commands in isolated per-agent Podman containers on a remote VM "
        "with persistent git worktree workspaces"
    ),
    tags=["tool", "sandbox", "vm", "ssh", "podman", "exec", "container"],
)
