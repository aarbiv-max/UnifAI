"""
Temporal adapter for background session submission.

Implements the session-level BackgroundSessionSubmitter port.
Starts a durable SessionWorkflow that owns the execution lifecycle
(begin → execute → complete/fail) inside the Temporal cluster.

Inputs are already staged into the SessionRecord by SessionInputProjector
before this submitter is called.

Uses string-based workflow invocation to avoid importing from the
inbound adapter layer (hexagonal boundary compliance).
"""
import asyncio
import uuid
from typing import Any, Dict, List, Optional

from mas.core.enums import ResourceCategory
from mas.session.execution.ports import BackgroundSessionSubmitter, SubmitSessionRequest
from mas.session.domain.workflow_session import WorkflowSession
from config.app_config import AppConfig
from temporal.client import get_temporal_client
from temporal.models import SessionWorkflowParams, GraphExecutionParams
from outbound.temporal.executor import TemporalGraphExecutor

_WORKFLOW_NAME = "SessionWorkflow"


class TemporalSessionSubmitter(BackgroundSessionSubmitter):
    """
    Submits sessions to Temporal for durable background execution.

    The SessionWorkflow handles the execution lifecycle:
      begin_session activity    → mark RUNNING
      GraphTraversalWorkflow    → graph execution (child workflow)
      complete_session activity → mark COMPLETED
      On error: fail_session    → mark FAILED

    Requires the session's executable_graph to be a TemporalGraphExecutor
    (both live in the same outbound/temporal adapter boundary).
    """

    def submit(self, session: WorkflowSession, request: SubmitSessionRequest) -> str:
        return asyncio.run(self._start_session_workflow(session, request))

    async def _start_session_workflow(
        self,
        session: WorkflowSession,
        request: SubmitSessionRequest,
    ) -> str:
        executor = session.executable_graph
        if not isinstance(executor, TemporalGraphExecutor):
            raise TypeError(
                f"TemporalSessionSubmitter requires a TemporalGraphExecutor, "
                f"got {type(executor).__name__}. "
                f"Ensure the session was built with engine_name='temporal'."
            )

        cfg = AppConfig.get_instance()
        client = await get_temporal_client()

        workflow_id = f"session-{session.get_run_id()}-{uuid.uuid4().hex[:8]}"

        sandbox_configs = self._extract_sandbox_configs(session)

        graph_params = GraphExecutionParams(
            state=session.graph_state,
            graph_definition=executor.graph_definition,
            session_id=session.get_run_id(),
            execution_context=request.execution_context,
        )
        params = SessionWorkflowParams(
            run_id=session.get_run_id(),
            execution_context=request.execution_context,
            graph_execution_params=graph_params,
            sandbox_configs=sandbox_configs,
        )
        await client.start_workflow(
            _WORKFLOW_NAME,
            params,
            id=workflow_id,
            task_queue=cfg.temporal_task_queue,
        )
        return workflow_id

    @staticmethod
    def _extract_sandbox_configs(
        session: WorkflowSession,
    ) -> Optional[List[Dict[str, Any]]]:
        """Extract sandbox_exec tool configs from the session registry.

        Returns None if no sandbox_exec tools exist in the blueprint,
        ensuring zero overhead for non-sandbox workflows.
        """
        configs: List[Dict[str, Any]] = []
        tool_instances = session.session_registry.all_of(ResourceCategory.TOOL)
        for rid, instance in tool_instances.items():
            if getattr(instance, "name", "").startswith("sandbox_exec"):
                cfg = session.session_registry.get_config(ResourceCategory.TOOL, rid)
                if cfg is not None:
                    configs.append(cfg.model_dump())
        return configs or None
