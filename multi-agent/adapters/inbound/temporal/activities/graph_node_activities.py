"""
Temporal activity wrapper for graph node and condition execution.

Composes a channel from the factory (adapter wiring) and delegates
the actual execution to the domain-level NodeExecutor.

Heartbeating and cooperative cancellation are handled by
``run_in_thread_with_heartbeat`` — the activity itself only manages
channel lifecycle.  On cancel the channel is closed so emit() becomes
a silent no-op; the agent thread finishes naturally.

pydantic_data_converter handles GraphState serialization/deserialization
automatically — no manual .serialize()/.deserialize() calls needed.
"""
import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from temporalio import activity

from mas.core.channels import ChannelFactory
from mas.engine.distributed.node_executor import NodeExecutor
from mas.graph.state.graph_state import GraphState
from inbound.temporal.activities.heartbeat import run_in_thread_with_heartbeat
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
        thread_pool: Optional[ThreadPoolExecutor] = None,
    ) -> None:
        self._executor = node_executor
        self._channel_factory = channel_factory
        self._thread_pool = thread_pool

    @activity.defn(name="execute_graph_node")
    async def execute_node(self, params: ExecuteNodeParams) -> GraphState:
        channel = None
        if self._channel_factory and params.session_id:
            channel = self._channel_factory.create(params.session_id)

        try:
            return await run_in_thread_with_heartbeat(
                functools.partial(
                    self._executor.execute_node,
                    node_uid=params.node_uid,
                    node_blueprint=params.node_blueprint,
                    step_context=params.step_context,
                    state=params.state,
                    channel=channel,
                    execution_context=params.execution_context,
                ),
                thread_pool=self._thread_pool,
            )
        except asyncio.CancelledError:
            if channel:
                channel.close(cancelled=True)
            raise

    @activity.defn(name="evaluate_condition")
    def evaluate_condition(self, params: EvaluateConditionParams) -> str:
        return self._executor.evaluate_condition(
            condition_rid=params.condition_rid,
            condition_blueprint=params.condition_blueprint,
            step_context=params.step_context,
            state=params.state,
        )
