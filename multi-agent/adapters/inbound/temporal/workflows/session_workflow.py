"""
Temporal session workflow — inbound adapter (parent workflow).

Implements BackgroundSessionOps with Temporal-specific mechanics
(activities, child workflows) and delegates the canonical lifecycle
ordering to BackgroundSessionRunner.

The ordering rule (begin → execute → complete/fail/cancel) lives in
session/execution/background_runner.py — NOT here.  This file
only supplies the HOW for each step.

Inputs are already staged into the SessionRecord before this workflow
starts.  begin() only transitions QUEUED → RUNNING.

pydantic_data_converter handles GraphState serialization/deserialization
automatically — no manual .serialize()/.deserialize() calls needed.
"""
import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import is_cancelled_exception

from mas.graph.state.graph_state import GraphState
from mas.session.domain.exceptions import SessionCancelledException
from mas.session.execution.background_runner import BackgroundSessionRunner
from temporal.models import (
    SessionWorkflowParams,
    GraphExecutionParams,
    BeginSessionParams,
    CompleteSessionParams,
    FailSessionParams,
    CancelSessionParams,
    ProvisionSandboxParams,
    TeardownSandboxParams,
)
from inbound.temporal.workflows.graph_traversal_workflow import GraphTraversalWorkflow

logger = logging.getLogger(__name__)

_LIFECYCLE_TIMEOUT = timedelta(seconds=30)
_LIFECYCLE_RETRY = RetryPolicy(maximum_attempts=3)

_GRAPH_WORKFLOW_TIMEOUT = timedelta(hours=1)
_SANDBOX_TIMEOUT = timedelta(minutes=5)
_SANDBOX_RETRY = RetryPolicy(maximum_attempts=2)

_SANDBOX_TOOL_TYPE = "sandbox_exec"


@workflow.defn
class SessionWorkflow:
    """
    Parent workflow for fire-and-forget session execution.

    Implements BackgroundSessionOps (structural typing via Protocol).
    Each method maps to a Temporal activity or child workflow.
    The runner drives the canonical ordering including cancel.
    """

    @workflow.run
    async def run(self, params: SessionWorkflowParams) -> GraphState:
        self._params = params
        self._sandbox_info = self._detect_sandbox_needs()

        if self._sandbox_info is not None:
            await self._provision_sandboxes()

        runner = BackgroundSessionRunner()
        try:
            result = await runner.run(self)
        except SessionCancelledException:
            await self._safe_teardown_sandboxes()
            raise asyncio.CancelledError()
        except asyncio.CancelledError:
            await self.cancel()
            await self._safe_teardown_sandboxes()
            raise
        except Exception:
            await self._safe_teardown_sandboxes()
            raise
        else:
            await self._safe_teardown_sandboxes()
            return result

    # ── BackgroundSessionOps implementation ──────────────────────────

    async def begin(self) -> GraphState:
        """Mark RUNNING, bind context, persist. Returns staged GraphState."""
        return await workflow.execute_activity(
            "begin_session",
            BeginSessionParams(
                run_id=self._params.run_id,
                execution_context=self._params.execution_context,
            ),
            start_to_close_timeout=_LIFECYCLE_TIMEOUT,
            retry_policy=_LIFECYCLE_RETRY,
            result_type=GraphState,
        )

    async def execute_graph(self, seeded_state: GraphState) -> GraphState:
        """Run graph traversal as a child workflow."""
        graph_params = GraphExecutionParams(
            state=seeded_state,
            graph_definition=self._params.graph_execution_params.graph_definition,
            session_id=self._params.run_id,
            execution_context=self._params.execution_context,
        )
        try:
            return await workflow.execute_child_workflow(
                GraphTraversalWorkflow.run,
                graph_params,
                id=f"{workflow.info().workflow_id}-graph",
                execution_timeout=_GRAPH_WORKFLOW_TIMEOUT,
                result_type=GraphState,
            )
        except Exception as e:
            if is_cancelled_exception(e):
                raise SessionCancelledException() from e
            raise

    async def complete(self, final_state: GraphState) -> None:
        """Attach final state, mark COMPLETED, persist."""
        await workflow.execute_activity(
            "complete_session",
            CompleteSessionParams(
                run_id=self._params.run_id,
                final_state=final_state,
            ),
            start_to_close_timeout=_LIFECYCLE_TIMEOUT,
            retry_policy=_LIFECYCLE_RETRY,
        )

    async def fail(self, error: Exception) -> None:
        """Mark FAILED, persist."""
        await workflow.execute_activity(
            "fail_session",
            FailSessionParams(
                run_id=self._params.run_id,
                error_message=str(error),
            ),
            start_to_close_timeout=_LIFECYCLE_TIMEOUT,
            retry_policy=_LIFECYCLE_RETRY,
        )

    async def cancel(self) -> None:
        """Mark CANCELLED, close channels, persist."""
        await workflow.execute_activity(
            "cancel_session",
            CancelSessionParams(run_id=self._params.run_id),
            start_to_close_timeout=_LIFECYCLE_TIMEOUT,
            retry_policy=_LIFECYCLE_RETRY,
        )

    # ── Sandbox lifecycle ───────────────────────────────────────────

    def _detect_sandbox_needs(
        self,
    ) -> Optional[Dict[str, Any]]:
        """Scan graph definition for nodes that use the sandbox_exec tool.

        Returns dict with agent_ids and sandbox_config, or None.
        """
        graph_def = self._params.graph_execution_params.graph_definition
        agent_ids: List[str] = []
        sandbox_config: Optional[Dict[str, Any]] = None

        for uid, node_def in graph_def.nodes.items():
            bp = node_def.node_blueprint
            for tool_spec in bp.get("tools", []):
                spec_type = tool_spec.get("type", "")
                cfg_block = tool_spec.get("config", {})
                cfg_type = cfg_block.get("type", "") if isinstance(cfg_block, dict) else ""
                if spec_type == _SANDBOX_TOOL_TYPE or cfg_type == _SANDBOX_TOOL_TYPE:
                    agent_ids.append(uid)
                    if sandbox_config is None:
                        sandbox_config = dict(cfg_block) if isinstance(cfg_block, dict) else {}
                    break

        if not agent_ids or sandbox_config is None:
            return None

        return {"agent_ids": agent_ids, "sandbox_config": sandbox_config}

    async def _provision_sandboxes(self) -> None:
        if self._sandbox_info is None:
            return
        await workflow.execute_activity(
            "provision_sandbox",
            ProvisionSandboxParams(
                run_id=self._params.run_id,
                agent_ids=self._sandbox_info["agent_ids"],
                sandbox_config=self._sandbox_info["sandbox_config"],
            ),
            start_to_close_timeout=_SANDBOX_TIMEOUT,
            retry_policy=_SANDBOX_RETRY,
        )

    async def _safe_teardown_sandboxes(self) -> None:
        if self._sandbox_info is None:
            return
        try:
            await workflow.execute_activity(
                "teardown_sandbox",
                TeardownSandboxParams(
                    run_id=self._params.run_id,
                    agent_ids=self._sandbox_info["agent_ids"],
                    sandbox_config=self._sandbox_info["sandbox_config"],
                ),
                start_to_close_timeout=_SANDBOX_TIMEOUT,
                retry_policy=_SANDBOX_RETRY,
            )
        except Exception:
            workflow.logger.warning(
                "Sandbox teardown failed for run %s", self._params.run_id,
                exc_info=True,
            )
