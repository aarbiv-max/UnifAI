"""
Temporal activity wrapper for graph node and condition execution.

Composes a channel from the factory (adapter wiring) and delegates
the actual execution to the domain-level NodeExecutor.

The @heartbeat decorator sends periodic heartbeats while the sync
activity body runs.  Cancellation is handled at the workflow level.

pydantic_data_converter handles GraphState serialization/deserialization
automatically — no manual .serialize()/.deserialize() calls needed.
"""
from typing import Optional

from temporalio import activity

from mas.core.channels import ChannelFactory
from mas.core.execution_context import ExecutionContext
from mas.engine.distributed.node_executor import NodeExecutor
from mas.graph.state.graph_state import GraphState
from inbound.temporal.activities.heartbeat import heartbeat
from temporal.models import ExecuteNodeParams, EvaluateConditionParams


class GraphNodeActivities:
    """
    Thin adapter — composes a channel from the factory (wiring)
    and delegates node execution to the domain NodeExecutor.
    """

    def __init__(
        self,
        node_executor: NodeExecutor,
        channel_factory: Optional[ChannelFactory] = None,
    ) -> None:
        self._executor = node_executor
        self._channel_factory = channel_factory

    @staticmethod
    def _enrich_context(params: ExecuteNodeParams) -> ExecutionContext:
        """Stamp run_id + node_uid into execution context tags."""
        return params.execution_context.model_copy(update={
            "tags": {
                **params.execution_context.tags,
                "run_id": params.session_id,
                "node_uid": params.node_uid,
            },
        })

    @activity.defn(name="execute_graph_node")
    @heartbeat(interval=3)
    def execute_node(self, params: ExecuteNodeParams) -> GraphState:
        channel = None
        if self._channel_factory and params.session_id:
            channel = self._channel_factory.create(params.session_id)

        enriched_ctx = self._enrich_context(params)

        return self._executor.execute_node(
            node_uid=params.node_uid,
            node_blueprint=params.node_blueprint,
            step_context=params.step_context,
            state=params.state,
            channel=channel,
            execution_context=enriched_ctx,
        )

    @activity.defn(name="evaluate_condition")
    def evaluate_condition(self, params: EvaluateConditionParams) -> str:
        return self._executor.evaluate_condition(
            condition_rid=params.condition_rid,
            condition_blueprint=params.condition_blueprint,
            step_context=params.step_context,
            state=params.state,
        )
