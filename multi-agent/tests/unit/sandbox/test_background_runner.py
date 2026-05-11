"""Tests for BackgroundSessionRunner — verify sandbox removal didn't break it.

Sandbox lifecycle was moved out of the runner and into the adapter
(SessionWorkflow).  These tests confirm the runner still works correctly
with its original 4-method Protocol.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from mas.graph.state.graph_state import GraphState
from mas.session.execution.background_runner import BackgroundSessionRunner


class TestBackgroundRunnerLifecycle:

    @pytest.fixture
    def mock_ops(self):
        ops = MagicMock()
        ops.begin = AsyncMock(return_value=GraphState())
        ops.execute_graph = AsyncMock(return_value=GraphState())
        ops.complete = AsyncMock()
        ops.fail = AsyncMock()
        return ops

    @pytest.mark.asyncio
    async def test_happy_path(self, mock_ops):
        runner = BackgroundSessionRunner()

        await runner.run(mock_ops)

        mock_ops.begin.assert_awaited_once()
        mock_ops.execute_graph.assert_awaited_once()
        mock_ops.complete.assert_awaited_once()
        mock_ops.fail.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fail_called_on_error(self, mock_ops):
        mock_ops.execute_graph.side_effect = RuntimeError("boom")
        runner = BackgroundSessionRunner()

        with pytest.raises(RuntimeError, match="boom"):
            await runner.run(mock_ops)

        mock_ops.fail.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_protocol_has_no_sandbox_methods(self):
        """Runner Protocol has exactly 4 methods — no sandbox awareness."""
        from mas.session.execution.background_runner import BackgroundSessionOps
        import inspect

        protocol_methods = {
            name for name, _ in inspect.getmembers(
                BackgroundSessionOps, predicate=inspect.isfunction
            )
            if not name.startswith("_")
        }
        assert "provision_sandboxes" not in protocol_methods
        assert "teardown_sandboxes" not in protocol_methods
        assert protocol_methods == {"begin", "execute_graph", "complete", "fail"}
