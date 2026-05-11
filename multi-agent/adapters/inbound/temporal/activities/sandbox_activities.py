"""Temporal activities for sandbox lifecycle (provision + teardown).

Thin adapter — delegates business logic to SandboxLifecycleService.
"""
import logging
from typing import Optional

from temporalio import activity

from mas.elements.tools.sandbox_exec.config import SandboxExecToolConfig
from mas.elements.tools.sandbox_exec.models import SandboxState
from mas.elements.tools.sandbox_exec.service import SandboxLifecycleService
from mas.session.management.user_session_manager import UserSessionManager
from mas.session.repository.repository import SessionRepository
from temporal.models import ProvisionSandboxParams, TeardownSandboxParams

logger = logging.getLogger(__name__)


class SandboxLifecycleActivities:
    """Temporal activity wrappers for sandbox provision and teardown."""

    def __init__(
        self,
        sandbox_service: SandboxLifecycleService,
        session_manager: UserSessionManager,
        session_repo: SessionRepository,
    ) -> None:
        self._sandbox_service = sandbox_service
        self._session_manager = session_manager
        self._session_repo = session_repo

    @activity.defn(name="provision_sandboxes")
    def provision(self, params: ProvisionSandboxParams) -> SandboxState:
        """Provision PVC and sandbox pods for every agent."""
        config = self._parse_config(params.sandbox_configs)

        existing_pvc: Optional[str] = None
        try:
            record = self._session_manager.get_record(params.run_id)
            existing_pvc = record.sandbox_pvc_name
        except KeyError:
            logger.info("Session record not yet persisted for %s; creating new PVC", params.run_id)

        activity.heartbeat("provisioning PVC and pods")

        sandbox_state = self._sandbox_service.provision_for_session(
            run_id=params.run_id,
            agent_ids=params.agent_ids,
            config=config,
            existing_pvc_name=existing_pvc,
        )

        try:
            record = self._session_manager.get_record(params.run_id)
            record.sandbox_pvc_name = sandbox_state.pvc_name
            self._session_repo.save(record)
        except KeyError:
            logger.warning("Could not persist PVC name — session record not found for %s", params.run_id)

        activity.heartbeat("provisioning complete")
        return sandbox_state

    @activity.defn(name="teardown_sandboxes")
    def teardown(self, params: TeardownSandboxParams) -> None:
        """Tear down sandbox pods.  Must never raise."""
        try:
            config = self._parse_config(params.sandbox_configs)
            if config is None:
                logger.warning("No sandbox config for teardown; skipping")
                return

            if params.sandbox_state is not None:
                self._sandbox_service.teardown_for_session(
                    params.sandbox_state, config,
                )
            else:
                self._sandbox_service.teardown_by_naming(
                    run_id=params.run_id,
                    agent_ids=params.agent_ids,
                    config=config,
                )
        except Exception:
            logger.exception("Sandbox teardown error (swallowed)")

    @staticmethod
    def _parse_config(
        sandbox_configs: Optional[list],
    ) -> Optional[SandboxExecToolConfig]:
        """Parse the first sandbox config dict into a typed model."""
        if not sandbox_configs:
            return None
        return SandboxExecToolConfig.model_validate(sandbox_configs[0])
