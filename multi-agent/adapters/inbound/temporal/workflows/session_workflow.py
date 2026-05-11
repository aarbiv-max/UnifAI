"""
Temporal session workflow — inbound adapter (parent workflow).

Implements BackgroundSessionOps with Temporal-specific mechanics
(activities, child workflows) and delegates the canonical lifecycle
ordering to BackgroundSessionRunner.

The ordering rule (begin → execute → complete/fail) lives in
session/execution/background_runner.py — NOT here.  This file
only supplies the HOW for each step.

Inputs are already staged into the SessionRecord before this workflow
starts.  begin() only transitions QUEUED → RUNNING.

pydantic_data_converter handles GraphState serialization/deserialization
automatically — no manual .serialize()/.deserialize() calls needed.
"""
from datetime import timedelta
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

from mas.elements.tools.sandbox_exec.models import SandboxState
from mas.graph.state.graph_state import GraphState
from mas.session.execution.background_runner import BackgroundSessionRunner
from temporal.models import (
    SessionWorkflowParams,
    GraphExecutionParams,
    BeginSessionParams,
    CompleteSessionParams,
    FailSessionParams,
    ProvisionSandboxParams,
    TeardownSandboxParams,
)
from inbound.temporal.workflows.graph_traversal_workflow import GraphTraversalWorkflow

_LIFECYCLE_TIMEOUT = timedelta(seconds=30)
_LIFECYCLE_RETRY = RetryPolicy(maximum_attempts=3)

_GRAPH_WORKFLOW_TIMEOUT = timedelta(hours=1)

_SANDBOX_PROVISION_TIMEOUT = timedelta(minutes=5)
_SANDBOX_HEARTBEAT_TIMEOUT = timedelta(minutes=2)
_SANDBOX_TEARDOWN_TIMEOUT = timedelta(minutes=2)
_SANDBOX_RETRY = RetryPolicy(maximum_attempts=3)


@workflow.defn
class SessionWorkflow:
    """
    Parent workflow for fire-and-forget session execution.

    Implements BackgroundSessionOps (structural typing via Protocol).
    Each method maps to a Temporal activity or child workflow.
    The runner drives the canonical ordering.
    """

    @workflow.run
    async def run(self, params: SessionWorkflowParams) -> GraphState:
        self._params = params
        self._sandbox_state: Optional[SandboxState] = None
        try:
            await self._provision_sandboxes()
            runner = BackgroundSessionRunner()
            return await runner.run(self)
        finally:
            await self._teardown_sandboxes()

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
        return await workflow.execute_child_workflow(
            GraphTraversalWorkflow.run,
            graph_params,
            id=f"{workflow.info().workflow_id}-graph",
            execution_timeout=_GRAPH_WORKFLOW_TIMEOUT,
            result_type=GraphState,
        )

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

    # ── Sandbox lifecycle (adapter concern, not part of Protocol) ──

    async def _provision_sandboxes(self) -> None:
        """Provision sandbox pods before graph execution (no-op if unused)."""
        if not self._params.sandbox_configs:
            return
        agent_ids = self._nodes_with_sandbox_tool()
        self._sandbox_state = await workflow.execute_activity(
            "provision_sandboxes",
            ProvisionSandboxParams(
                run_id=self._params.run_id,
                agent_ids=agent_ids,
                sandbox_configs=self._params.sandbox_configs,
            ),
            start_to_close_timeout=_SANDBOX_PROVISION_TIMEOUT,
            heartbeat_timeout=_SANDBOX_HEARTBEAT_TIMEOUT,
            retry_policy=_SANDBOX_RETRY,
            result_type=SandboxState,
        )

    async def _teardown_sandboxes(self) -> None:
        """Tear down sandbox pods (always runs via finally, must not raise)."""
        if not self._params.sandbox_configs:
            return
        try:
            agent_ids = self._nodes_with_sandbox_tool()
            await workflow.execute_activity(
                "teardown_sandboxes",
                TeardownSandboxParams(
                    run_id=self._params.run_id,
                    sandbox_state=self._sandbox_state,
                    sandbox_configs=self._params.sandbox_configs,
                    agent_ids=agent_ids,
                ),
                start_to_close_timeout=_SANDBOX_TEARDOWN_TIMEOUT,
                retry_policy=_SANDBOX_RETRY,
            )
        except Exception:
            workflow.logger.exception("Sandbox teardown activity failed (swallowed)")

    def _nodes_with_sandbox_tool(self) -> list:
        """Return only node UIDs whose mini-blueprint includes a sandbox_exec tool."""
        nodes = self._params.graph_execution_params.graph_definition.nodes
        result = []
        for uid, node_def in nodes.items():
            tools = node_def.node_blueprint.get("tools", [])
            if any(t.get("type") == "sandbox_exec" for t in tools):
                result.append(uid)
        return result
