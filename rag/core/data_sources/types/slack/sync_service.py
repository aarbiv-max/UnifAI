"""Slack incremental sync service — scheduled re-embedding use case."""
from datetime import datetime, timezone
from typing import Dict, Any

from core.data_sources.domain.model import DataSource
from core.data_sources.domain.repository import DataSourceRepository
from core.pipeline.domain.dispatcher import PipelineTaskDispatcher
from shared.logger import logger


class SlackSyncService:
    """
    Application use case: incrementally sync all registered Slack sources.

    Queries every Slack source and dispatches an individual pipeline task
    for each one bounded by ``[last_sync_at, now)``.  Per-source retries,
    timeouts, and failure isolation are handled by the task infrastructure
    (Celery), not by this service.
    """

    def __init__(
        self,
        source_repo: DataSourceRepository,
        task_dispatcher: PipelineTaskDispatcher,
    ) -> None:
        self._source_repo = source_repo
        self._dispatcher = task_dispatcher

    def sync_one(self, source_id: str) -> Dict[str, Any]:
        """
        Dispatch a pipeline task for a single Slack source.

        Args:
            source_id: The channel ID to sync.

        Returns:
            Dict with dispatch status.

        Raises:
            ValueError: If the source is not found.
        """
        source = self._source_repo.find_by_id(source_id)
        if not source:
            raise ValueError(f"Slack source not found: {source_id}")

        self._dispatch_source(source)
        logger.info("Manual sync dispatched for source %s", source_id)
        return {"source_id": source_id, "status": "dispatched"}

    def sync_all(self) -> Dict[str, Any]:
        """
        Dispatch a pipeline task for every registered Slack source.

        Returns:
            Summary dict with dispatched count and any dispatch errors.
        """
        sources = self._source_repo.find_all(source_type="SLACK")

        dispatched = 0
        errors = []

        for source in sources:
            try:
                self._dispatch_source(source)
                dispatched += 1
            except Exception as exc:
                logger.error(
                    "Failed to dispatch sync for %s: %s",
                    source.source_id, exc, exc_info=True,
                )
                errors.append({"source_id": source.source_id, "error": str(exc)})

        logger.info("Slack sync dispatched=%d  errors=%d", dispatched, len(errors))
        return {"dispatched": dispatched, "errors": errors}

    def _dispatch_source(self, source: DataSource) -> None:
        """Build payload and dispatch a pipeline task for a single source."""
        oldest = source.last_sync_at or source.created_at
        self._dispatcher.dispatch(
            source_type="SLACK",
            source_data=self._build_source_data(source, oldest),
        )

    @staticmethod
    def _build_source_data(source: DataSource, oldest: datetime) -> Dict[str, Any]:
        """Build the payload expected by ``build_context`` in pipeline_tasks."""
        # Ensure the timestamp is timezone-aware UTC so that downstream
        # conversion to unix seconds (via .timestamp()) is correct.
        if oldest.tzinfo is None:
            oldest = oldest.replace(tzinfo=timezone.utc)
        type_data = {
            **source.type_data,
            "start_timestamp": oldest.isoformat(),
        }
        return {
            "pipeline_id": source.pipeline_id,
            "metadata": {
                "channel_id": source.source_id,
                "channel_name": source.source_name,
                "is_private": source.type_data.get("is_private", False),
            },
            "type_data": type_data,
        }
