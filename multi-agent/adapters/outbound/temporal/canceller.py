"""
Temporal adapter for background session cancellation.

Implements the session-level BackgroundSessionCanceller port.
Sends a cancellation request to the Temporal workflow.  The workflow's
CancelledError handler triggers the cancel_session activity which owns
the lifecycle transition and channel cleanup via BackgroundLifecycleHandler.

Uses the same asyncio.run() pattern as TemporalSessionSubmitter
for calling async Temporal client from synchronous Flask context.
"""
import asyncio
import logging

from mas.session.execution.ports import BackgroundSessionCanceller
from temporal.client import get_temporal_client

logger = logging.getLogger(__name__)


class TemporalSessionCanceller(BackgroundSessionCanceller):

    def cancel(self, session_id: str) -> None:
        try:
            asyncio.run(self._cancel_workflow(session_id))
        except Exception:
            logger.warning(
                "Failed to cancel Temporal workflow for session %s "
                "(may have already completed)",
                session_id, exc_info=True,
            )

    async def _cancel_workflow(self, session_id: str) -> None:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(f"session-{session_id}")
        await handle.cancel()
