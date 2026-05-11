"""
Temporal activity wrapper for graph node and condition execution.

Composes a channel from the factory (adapter wiring) and delegates
the actual execution to the domain-level NodeExecutor.

pydantic_data_converter handles GraphState serialization/deserialization
automatically — no manual .serialize()/.deserialize() calls needed.
"""
from typing import Optional

from temporalio import activity

from mas.core.channels import ChannelFactory
from mas.core.execution_context import ExecutionContext
from mas.engine.distributed.node_executor import NodeExecutor
from mas.graph.state.graph_state import GraphState
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

    @activity.defn(name="execute_graph_node")
    def execute_node(self, params: ExecuteNodeParams) -> GraphState:
        channel = None
        if self._channel_factory and params.session_id:
            channel = self._channel_factory.create(params.session_id)

        execution_context = self._enrich_context(params)

        return self._executor.execute_node(
            node_uid=params.node_uid,
            node_blueprint=params.node_blueprint,
            step_context=params.step_context,
            state=params.state,
            channel=channel,
            execution_context=execution_context,
        )

    @staticmethod
    def _enrich_context(params: ExecuteNodeParams) -> Optional[ExecutionContext]:
        """Add runtime identity tags so tools can resolve per-node resources.

        Enrichment happens here in the adapter — the engine stays
        agnostic to session/node identity concerns.
        """
        if not params.execution_context:
            return None
        return params.execution_context.model_copy(update={
            "tags": {
                **params.execution_context.tags,
                "run_id": params.session_id,
                "node_uid": params.node_uid,
            }
        })

    @activity.defn(name="evaluate_condition")
    def evaluate_condition(self, params: EvaluateConditionParams) -> str:
        return self._executor.evaluate_condition(
            condition_rid=params.condition_rid,
            condition_blueprint=params.condition_blueprint,
            step_context=params.step_context,
            state=params.state,
        )
