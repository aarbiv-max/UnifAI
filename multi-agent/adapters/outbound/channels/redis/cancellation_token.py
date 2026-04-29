"""
Redis-backed cancellation token.

Uses a simple key (``mas:cancelled:{session_id}``) whose existence
signals that the session has been cancelled.  Once detected, the
result is cached locally so subsequent checks are free.
"""
from redis import Redis

from mas.core.channels import CancellationToken

from .constants import CANCELLED_PREFIX


class RedisCancellationToken(CancellationToken):
    """Redis-backed cancellation token.

    Checks for the existence of a ``mas:cancelled:{session_id}`` key.
    Once detected, caches the result locally to avoid further Redis calls.
    """

    def __init__(self, session_id: str, redis_client: Redis) -> None:
        self._session_id = session_id
        self._redis = redis_client
        self._cancelled = False

    def is_cancelled(self) -> bool:
        if self._cancelled:
            return True
        if self._redis.exists(f"{CANCELLED_PREFIX}{self._session_id}"):
            self._cancelled = True
            return True
        return False

    def mark_cancelled(self, ttl: int = 90) -> None:
        """Set the cancellation flag in Redis with a TTL."""
        self._redis.set(
            f"{CANCELLED_PREFIX}{self._session_id}",
            "1",
            ex=ttl,
        )
        self._cancelled = True

    def clear(self) -> None:
        """Remove a stale cancellation flag."""
        self._redis.delete(f"{CANCELLED_PREFIX}{self._session_id}")
        self._cancelled = False
