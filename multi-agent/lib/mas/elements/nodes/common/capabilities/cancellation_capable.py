"""
Cancellation capability mixin for nodes.
Provides cooperative cancellation via an injectable check function.
"""
from typing import Callable, Optional


class CancellationCapableMixin:
    """
    Mixin that provides cancellation capability to nodes.

    Mirrors StreamingCapableMixin: injected before execution, queried during.
    Accepts a plain callable so the domain layer stays free of concurrency
    primitives. The adapter supplies the concrete check (e.g. threading.Event.is_set).
    When no check is injected, is_cancelled() always returns False (inert).
    """

    _cancel_check: Optional[Callable[[], bool]] = None

    def set_cancel_check(self, check: Optional[Callable[[], bool]]) -> None:
        """Inject the cancellation check before execution."""
        self._cancel_check = check

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        return self._cancel_check is not None and self._cancel_check()
