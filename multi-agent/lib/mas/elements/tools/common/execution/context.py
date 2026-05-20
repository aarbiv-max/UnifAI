"""
Context variables for cross-cutting tool execution state.

Uses Python's contextvars module to propagate caller identity across
asyncio.to_thread boundaries without mutable shared state on tool instances.
"""
import contextvars

caller_uid_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "caller_uid", default=""
)
