"""Temporal activity wrappers for sandbox lifecycle operations.

Thin adapter that delegates to ``SandboxLifecycleService``.
"""
import logging

from temporalio import activity

from mas.elements.tools.sandbox_exec.config import SandboxExecToolConfig
from mas.elements.tools.sandbox_exec.service import SandboxLifecycleService
from inbound.temporal.activities.heartbeat import heartbeat
from temporal.models import ProvisionSandboxParams, TeardownSandboxParams

logger = logging.getLogger(__name__)


class SandboxLifecycleActivities:
    """Activity wrapper for sandbox provisioning/teardown."""

    def __init__(self, lifecycle_service: SandboxLifecycleService) -> None:
        self._service = lifecycle_service

    @activity.defn(name="provision_sandbox")
    @heartbeat(interval=5)
    def provision(self, params: ProvisionSandboxParams) -> None:
        """Provision bare repo + worktrees + containers for all agents."""
        config = SandboxExecToolConfig(**params.sandbox_config)
        self._service.provision_for_session(
            run_id=params.run_id,
            agent_ids=params.agent_ids,
            config=config,
        )

    @activity.defn(name="teardown_sandbox")
    def teardown(self, params: TeardownSandboxParams) -> None:
        """Tear down sandbox containers using deterministic naming."""
        config = SandboxExecToolConfig(**params.sandbox_config)
        self._service.teardown_by_naming(
            run_id=params.run_id,
            agent_ids=params.agent_ids,
            config=config,
        )
