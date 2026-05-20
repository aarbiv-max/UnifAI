"""Unit tests for cleanup lifecycle integration.

Tests that ForegroundSessionRunner._cleanup_tools calls cleanup() on tools
and that BaseTool.cleanup() is a safe no-op.
"""
from unittest.mock import MagicMock, patch

from mas.elements.tools.common.base_tool import BaseTool
from mas.core.enums import ResourceCategory


class ConcreteTool(BaseTool):
    name = "test_tool"
    description = "test"

    def run(self, *args, **kwargs):
        return "ok"


class TestBaseToolCleanup:
    def test_cleanup_is_noop(self):
        tool = ConcreteTool()
        tool.cleanup()

    def test_cleanup_can_be_overridden(self):
        class CustomTool(BaseTool):
            name = "custom"
            description = "custom"
            cleaned = False

            def run(self, *a, **kw):
                return ""

            def cleanup(self):
                self.cleaned = True

        tool = CustomTool()
        tool.cleanup()
        assert tool.cleaned is True


class TestCleanupTools:
    """Test the _cleanup_tools static method pattern."""

    def test_cleanup_tools_calls_cleanup_on_all_tools(self):
        tool1 = MagicMock()
        tool1.cleanup = MagicMock()
        tool2 = MagicMock()
        tool2.cleanup = MagicMock()

        session = MagicMock()
        session.session_registry.all_of.return_value = {
            "tool-1": tool1,
            "tool-2": tool2,
        }

        from mas.session.execution.foreground_runner import ForegroundSessionRunner
        ForegroundSessionRunner._cleanup_tools(session)

        tool1.cleanup.assert_called_once()
        tool2.cleanup.assert_called_once()

    def test_cleanup_tools_survives_exception(self):
        tool1 = MagicMock()
        tool1.cleanup.side_effect = RuntimeError("boom")
        tool2 = MagicMock()
        tool2.cleanup = MagicMock()

        session = MagicMock()
        session.session_registry.all_of.return_value = {
            "tool-1": tool1,
            "tool-2": tool2,
        }

        from mas.session.execution.foreground_runner import ForegroundSessionRunner
        ForegroundSessionRunner._cleanup_tools(session)

        tool2.cleanup.assert_called_once()

    def test_cleanup_tools_skips_tools_without_cleanup(self):
        tool_no_cleanup = MagicMock(spec=[])  # no cleanup attr

        session = MagicMock()
        session.session_registry.all_of.return_value = {
            "tool-1": tool_no_cleanup,
        }

        from mas.session.execution.foreground_runner import ForegroundSessionRunner
        ForegroundSessionRunner._cleanup_tools(session)
