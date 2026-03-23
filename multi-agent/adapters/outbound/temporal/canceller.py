"""
Temporal adapter for background session cancellation.

Implements the session-level BackgroundSessionCanceller port.
Notifies subscribers via Redis channel (immediate), then requests
Temporal workflow cancellation (graceful).

Uses the same asyncio.run() pattern as TemporalSessionSubmitter
for calling async Temporal client from synchronous Flask context.
"""
import asyncio
import logging
from typing import Optional

from mas.core.channels import ChannelFactory
from mas.session.execution.ports import BackgroundSessionCanceller
from temporal.client import get_temporal_client

logger = logging.getLogger(__name__)


class TemporalSessionCanceller(BackgroundSessionCanceller):

    def __init__(self, channel_factory: Optional[ChannelFactory] = None):
        self._channel_factory = channel_factory

    def cancel(self, session_id: str) -> None:
        try:
            self._notify_subscribers(session_id)
        except Exception:
            logger.warning(
                "Failed to notify subscribers for session %s",
                session_id, exc_info=True,
            )
        try:
            asyncio.run(self._cancel_workflow(session_id))
        except Exception:
            logger.warning(
                "Failed to cancel Temporal workflow for session %s "
                "(may have already completed)",
                session_id, exc_info=True,
            )

    def _notify_subscribers(self, session_id: str) -> None:
        if self._channel_factory:
            channel = self._channel_factory.create(session_id)
            channel.emit({"type": "session_cancelled"})
            channel.close()

    async def _cancel_workflow(self, session_id: str) -> None:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(f"session-{session_id}")
        await handle.cancel()
