"""Unit tests for execution context enrichment (both Temporal and Foreground paths)."""
import pytest
from unittest.mock import MagicMock

from mas.core.execution_context import ExecutionContext, ExecutionContextHolder
from temporal.models import ExecuteNodeParams
from mas.graph.state.graph_state import GraphState


class TestGraphNodeActivitiesEnrichContext:
    """Test _enrich_context static method from GraphNodeActivities."""

    def test_stamps_run_id_and_node_uid(self):
        from inbound.temporal.activities.graph_node_activities import GraphNodeActivities

        params = ExecuteNodeParams(
            node_uid="agent-1",
            session_id="session-abc",
            execution_context=ExecutionContext(tags={"existing": "value"}),
        )
        enriched = GraphNodeActivities._enrich_context(params)
        assert enriched is not None
        assert enriched.tags["run_id"] == "session-abc"
        assert enriched.tags["node_uid"] == "agent-1"
        assert enriched.tags["existing"] == "value"

    def test_preserves_original_context_fields(self):
        from inbound.temporal.activities.graph_node_activities import GraphNodeActivities

        params = ExecuteNodeParams(
            node_uid="agent-1",
            session_id="session-abc",
            execution_context=ExecutionContext(user_id="u1", scope="private"),
        )
        enriched = GraphNodeActivities._enrich_context(params)
        assert enriched.user_id == "u1"
        assert enriched.scope == "private"


class TestNodeExecutorEnrichment:
    """Test that NodeExecutor stamps node_uid into the execution context."""

    def test_enriches_context_with_node_uid(self):
        """Verify that execute_node adds node_uid to the execution context tags
        before passing them to the built plan's execution context holder."""
        from unittest.mock import patch
        from mas.engine.distributed.node_executor import NodeExecutor
        from mas.blueprints.models.blueprint import BlueprintSpec

        mock_factory = MagicMock()
        mock_plan = MagicMock()
        mock_step = MagicMock()
        mock_step.func.return_value = GraphState()
        mock_plan.get_step.return_value = mock_step
        mock_factory.build_runtime_plan.return_value = mock_plan

        executor = NodeExecutor(session_factory=mock_factory)
        ctx = ExecutionContext(tags={"run_id": "r1"})

        mock_bp = MagicMock(spec=BlueprintSpec)
        with patch("mas.engine.distributed.node_executor.BlueprintSpec") as bp_cls:
            bp_cls.model_validate.return_value = mock_bp
            executor.execute_node(
                node_uid="agent-x",
                node_blueprint={},
                step_context=None,
                state=GraphState(),
                execution_context=ctx,
            )

        build_call = mock_factory.build_runtime_plan.call_args
        holder = build_call.kwargs.get("ctx_holder") or build_call[1].get("ctx_holder")

        assert holder.context.tags["node_uid"] == "agent-x"
        assert holder.context.tags["run_id"] == "r1"


class TestBaseNodeHolderInjection:
    """Test that BaseNode.__call__ stamps node_uid from StepContext into the holder."""

    def test_stamps_node_uid_on_call(self):
        from mas.graph.models import StepContext

        class DummyNode:
            pass

        from mas.elements.nodes.common.base_node import BaseNode

        class TestNode(BaseNode):
            READS = set()
            WRITES = set()

            def run(self, state):
                return state

        holder = ExecutionContextHolder()
        holder.context = ExecutionContext(tags={"run_id": "r1"})

        node = TestNode()
        node.set_context(StepContext(uid="my-agent"))
        node.set_execution_holder(holder)

        node(GraphState(), config={})
        assert holder.context.tags["node_uid"] == "my-agent"

    def test_no_crash_without_holder(self):
        from mas.graph.models import StepContext
        from mas.elements.nodes.common.base_node import BaseNode

        class TestNode(BaseNode):
            READS = set()
            WRITES = set()

            def run(self, state):
                return state

        node = TestNode()
        node.set_context(StepContext(uid="agent-1"))
        node(GraphState(), config={})
