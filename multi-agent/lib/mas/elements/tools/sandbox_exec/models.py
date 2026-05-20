"""Runtime models for sandbox state.

These models live only in workflow instance variables during execution.
They are NOT persisted to any database.
"""
from typing import Dict, Literal

from pydantic import BaseModel, Field


class SandboxContainerInfo(BaseModel):
    """Ephemeral per-agent container state."""

    agent_id: str
    container_name: str
    worktree_path: str
    status: Literal["provisioning", "ready", "terminated", "failed"] = "provisioning"


class SandboxState(BaseModel):
    """Aggregate sandbox state for a workflow run."""

    session_id: str
    vm_host: str
    containers: Dict[str, SandboxContainerInfo] = Field(default_factory=dict)
