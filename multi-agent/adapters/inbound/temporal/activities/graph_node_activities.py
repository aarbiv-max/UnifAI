"""
Temporal activity wrapper for graph node and condition execution.

Composes a channel from the factory (adapter wiring) and delegates
the actual execution to the domain-level NodeExecutor.

The execute_node activity is async to support a heartbeat polling loop
that enables Temporal's cooperative cancellation mechanism.

pydantic_data_converter handles GraphState serialization/deserialization
automatically — no manual .serialize()/.deserialize() calls needed.
"""
import asyncio
import functools
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from temporalio import activity

from mas.core.channels import ChannelFactory
from mas.engine.distributed.node_executor import NodeExecutor
from mas.graph.state.graph_state import GraphState
from temporal.models import ExecuteNodeParams, EvaluateConditionParams

HEARTBEAT_INTERVAL_S = 5
GRACE_PERIOD_S = 10


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
        cancel_event = threading.Event()

        channel = None
        if self._channel_factory and params.session_id:
            channel = self._channel_factory.create(params.session_id)

        future = asyncio.get_running_loop().run_in_executor(
            self._thread_pool,
            functools.partial(
                self._executor.execute_node,
                node_uid=params.node_uid,
                node_blueprint=params.node_blueprint,
                step_context=params.step_context,
                state=params.state,
                channel=channel,
                execution_context=params.execution_context,
                cancel_check=cancel_event.is_set,
            ),
        )

        try:
            return await self._heartbeat_until_done(future)
        except asyncio.CancelledError:
            cancel_event.set()
            await self._await_graceful_shutdown(future)
            if channel:
                channel.close()
            raise

    async def _heartbeat_until_done(self, future: asyncio.Future) -> GraphState:
        """Poll the executor future, sending heartbeats while it runs."""
        while not future.done():
            try:
                return await asyncio.wait_for(
                    asyncio.shield(future), timeout=HEARTBEAT_INTERVAL_S
                )
            except asyncio.TimeoutError:
                activity.heartbeat("running")
        return future.result()

    async def _await_graceful_shutdown(self, future: asyncio.Future) -> None:
        """Give the worker thread a grace period to finish after cancellation."""
        if future.done():
            return
        try:
            await asyncio.wait_for(
                asyncio.shield(future), timeout=GRACE_PERIOD_S
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass

    @activity.defn(name="evaluate_condition")
    def evaluate_condition(self, params: EvaluateConditionParams) -> str:
        return self._executor.evaluate_condition(
            condition_rid=params.condition_rid,
            condition_blueprint=params.condition_blueprint,
            step_context=params.step_context,
            state=params.state,
        )
