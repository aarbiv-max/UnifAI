"""
Reusable heartbeat utilities for Temporal activities.

Provides both a helper function and a decorator to run synchronous work
in a thread pool while sending Temporal heartbeats.  The heartbeat call
serves dual duty: it keeps the activity alive AND detects workflow
cancellation (``activity.heartbeat()`` raises ``CancelledError`` when
the workflow has been cancelled).

Use ``run_in_thread_with_heartbeat`` when the activity needs
setup/cleanup around the threaded work (e.g. channel creation).
Use ``with_activity_heartbeat`` as a decorator for simple activities
whose entire body can run in a thread.
"""
import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional, TypeVar

from temporalio import activity

T = TypeVar("T")

HEARTBEAT_INTERVAL_S = 5
GRACE_PERIOD_S = 10


async def run_in_thread_with_heartbeat(
    fn: Callable[..., T],
    *,
    thread_pool: Optional[ThreadPoolExecutor] = None,
    interval_s: float = HEARTBEAT_INTERVAL_S,
    grace_s: float = GRACE_PERIOD_S,
) -> T:
    """
    Run *fn* in a thread pool, heartbeating until it completes.

    On ``CancelledError`` (workflow cancelled), the thread is given a
    grace period to finish before the error is re-raised.
    """
    future = asyncio.get_running_loop().run_in_executor(thread_pool, fn)
    try:
        while not future.done():
            try:
                return await asyncio.wait_for(
                    asyncio.shield(future), timeout=interval_s
                )
            except asyncio.TimeoutError:
                activity.heartbeat("running")
        return future.result()
    except asyncio.CancelledError:
        if not future.done():
            try:
                await asyncio.wait_for(
                    asyncio.shield(future), timeout=grace_s
                )
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        raise


def with_activity_heartbeat(
    interval_s: float = HEARTBEAT_INTERVAL_S,
    grace_s: float = GRACE_PERIOD_S,
):
    """
    Decorator that runs a sync activity function in a thread with heartbeats.

    Suitable for activities whose entire body is synchronous and needs
    no async setup/cleanup.  For activities that require channel creation
    or cleanup on cancel, use ``run_in_thread_with_heartbeat`` directly.
    """
    def decorator(fn: Callable[..., T]) -> Callable[..., Any]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await run_in_thread_with_heartbeat(
                functools.partial(fn, *args, **kwargs),
                interval_s=interval_s,
                grace_s=grace_s,
            )
        return wrapper
    return decorator
