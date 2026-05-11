"""Runtime models for sandbox state.

These models live only in Temporal workflow instance variables during
execution.  They are NOT persisted to any database.  The only persisted
sandbox reference is ``SessionRecord.sandbox_pvc_name``.
"""
from typing import Dict, Literal

from pydantic import BaseModel, Field


class SandboxPodInfo(BaseModel):
    """Ephemeral per-agent pod state."""

    agent_id: str
    pod_name: str
    namespace: str
    worktree_path: str
    branch_name: str
    status: Literal["provisioning", "ready", "terminated", "failed"] = "provisioning"


class SandboxState(BaseModel):
    """Aggregate sandbox state for a workflow run."""

    session_id: str
    pvc_name: str
    cluster_api: str
    namespace: str
    git_repo_url: str
    pods: Dict[str, SandboxPodInfo] = Field(default_factory=dict)
