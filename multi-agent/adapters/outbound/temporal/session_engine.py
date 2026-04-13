"""
Temporal adapter for background session operations.

Implements the BackgroundSessionEngine port — submit and cancel
session workflows via the Temporal client.

Uses asyncio.run() to bridge from synchronous Flask context
into Temporal's async API.
"""
import asyncio
import uuid
import logging
from typing import Optional

from mas.session.execution.ports import BackgroundSessionEngine, SubmitSessionRequest
from mas.session.domain.workflow_session import WorkflowSession
from config.app_config import AppConfig
from temporal.client import get_temporal_client
from temporal.models import SessionWorkflowParams, GraphExecutionParams
from outbound.temporal.executor import TemporalGraphExecutor

logger = logging.getLogger(__name__)

_WORKFLOW_NAME = "SessionWorkflow"


class TemporalSessionEngine(BackgroundSessionEngine):
    """
    Temporal implementation of background session operations.

    submit():
      Starts a durable SessionWorkflow that owns the execution lifecycle
      (begin → execute → complete/fail) inside the Temporal cluster.
      Requires the session's executable_graph to be a TemporalGraphExecutor.

    cancel():
      Sends a cancellation request to the Temporal workflow.  The workflow's
      CancelledError handler triggers the cancel_session activity which owns
      the lifecycle transition and channel cleanup via BackgroundLifecycleHandler.
    """

    def submit(self, session: WorkflowSession, request: SubmitSessionRequest) -> str:
        return asyncio.run(self._start_session_workflow(session, request))

    def cancel(self, session_id: str, workflow_id: Optional[str] = None) -> None:
        if not workflow_id:
            logger.warning(
                "No workflow_id available for session %s — cannot cancel",
                session_id,
            )
            return
        try:
            asyncio.run(self._cancel_workflow(workflow_id))
        except Exception:
            logger.warning(
                "Failed to cancel Temporal workflow %s for session %s "
                "(may have already completed)",
                workflow_id, session_id, exc_info=True,
            )

    async def _start_session_workflow(
        self,
        session: WorkflowSession,
        request: SubmitSessionRequest,
    ) -> str:
        executor = session.executable_graph
        if not isinstance(executor, TemporalGraphExecutor):
            raise TypeError(
                f"TemporalSessionEngine requires a TemporalGraphExecutor, "
                f"got {type(executor).__name__}. "
                f"Ensure the session was built with engine_name='temporal'."
            )

        cfg = AppConfig.get_instance()
        client = await get_temporal_client()

        workflow_id = f"session-{session.get_run_id()}-{uuid.uuid4().hex[:8]}"

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
        )
        await client.start_workflow(
            _WORKFLOW_NAME,
            params,
            id=workflow_id,
            task_queue=cfg.temporal_task_queue,
        )
        return workflow_id

    async def _cancel_workflow(self, workflow_id: str) -> None:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.cancel()
