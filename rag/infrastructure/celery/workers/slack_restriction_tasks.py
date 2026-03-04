"""
Slack channel restriction reconciliation — Celery task (driving adapter).

Enqueued by the /clean-restricted-channels endpoint when the backend
ActionDispatcher notifies RAG of a restriction-rules change.
"""
from global_utils.celery_app import CeleryApp
from bootstrap.app_container import slack_channel_service
from shared.logger import logger


@CeleryApp().app.task(bind=True, max_retries=3, default_retry_delay=30)
def reconcile_restrictions_task(self):
    """Re-evaluate every cached channel against the latest restriction rules."""
    try:
        logger.info("Starting async channel restriction reconciliation")
        result = slack_channel_service().reconcile_restrictions()
        summary = {
            "newly_restricted": result.newly_restricted,
            "newly_unrestricted": result.newly_unrestricted,
            "failed_deletions": result.failed_deletions,
        }
        logger.info(
            "Reconciliation complete — restricted %d, unrestricted %d, "
            "failed deletions %d",
            len(result.newly_restricted),
            len(result.newly_unrestricted),
            len(result.failed_deletions),
        )
        return summary
    except Exception as e:
        logger.error(f"Reconciliation failed: {e}", exc_info=True)
        raise self.retry(exc=e)
