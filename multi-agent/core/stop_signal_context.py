"""
Stop signal context for cross-layer communication.

Provides a ContextVar-based mechanism for checking stop signals at any level
of the execution stack (SessionExecutor, AgentIterator, ToolExecutor, etc.).

This allows stop signals to be checked at multiple points in the execution
chain, not just between LangGraph chunks.
"""
from contextvars import ContextVar
from typing import Optional, Callable

# Type alias for stop signal checker function
StopSignalChecker = Callable[[], bool]

# ContextVar to hold the current stop signal checker
_stop_checker: ContextVar[Optional[StopSignalChecker]] = ContextVar(
    "stop_signal_checker",
    default=None
)


def set_stop_signal_checker(checker: Optional[StopSignalChecker]) -> None:
    """
    Set the stop signal checker for the current execution context.
    
    Args:
        checker: A callable that returns True if execution should stop,
                 or None to clear the checker
    """
    _stop_checker.set(checker)


def clear_stop_signal_checker() -> None:
    """Clear the stop signal checker for the current context."""
    _stop_checker.set(None)


def should_stop() -> bool:
    """
    Check if execution should stop.
    
    Can be called from anywhere in the execution stack to check if
    a stop signal has been received.
    
    Returns:
        True if execution should stop, False otherwise.
        Returns False if no checker is set.
    """
    checker = _stop_checker.get()
    if checker is None:
        return False
    try:
        return checker()
    except Exception:
        # If checker fails, don't stop (fail-safe)
        return False


class StoppedExecutionError(Exception):
    """
    Exception raised when execution is stopped by user.
    
    This exception is caught by SessionExecutor to handle graceful stopping.
    """
    def __init__(self, message: str = "Execution stopped by user"):
        self.message = message
        super().__init__(self.message)
