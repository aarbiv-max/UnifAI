"""
Slack incremental sync Celery task — driving adapter.

Orchestrator task triggered by Celery Beat every 12 hours.
Dispatches an individual pipeline task per Slack source;
per-source retries and isolation are handled by the pipeline workers.
"""
from global_utils.celery_app import CeleryApp
from bootstrap.app_container import slack_sync_service
from shared.logger import logger


@CeleryApp().app.task
def slack_incremental_sync_task():
    """
    Periodic orchestrator: dispatch a pipeline task for every registered
    Slack source since its last successful sync.
    """
    logger.info("Starting scheduled Slack incremental sync")
    result = slack_sync_service().sync_all()
    logger.info(f"Slack incremental sync finished: {result}")
    return result
