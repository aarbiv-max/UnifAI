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
from typing import Optional

from mas.session.execution.ports import BackgroundSessionCanceller
from temporal.client import get_temporal_client

logger = logging.getLogger(__name__)


class TemporalSessionCanceller(BackgroundSessionCanceller):

    def cancel(self, session_id: str, workflow_id: Optional[str] = None) -> None:
        if not workflow_id:
            logger.warning(
                "No workflow_id available for session %s — cannot cancel",
                session_id,
            )
            return
        try:
            asyncio.run(self._cancel_workflow(workflow_id))
        except Exception:
            logger.warning(
                "Failed to cancel Temporal workflow %s for session %s "
                "(may have already completed)",
                workflow_id, session_id, exc_info=True,
            )

    async def _cancel_workflow(self, workflow_id: str) -> None:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.cancel()
