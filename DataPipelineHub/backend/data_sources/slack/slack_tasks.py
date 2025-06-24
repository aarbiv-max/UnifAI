from global_utils.celery_app import CeleryApp
from providers.slack import embed_slack_channels_flow
from shared.logger import logger

@CeleryApp().app.task(bind=True, max_retries=5, default_retry_delay=60)
def embed_slack_channels_task(self, channel_list, upload_by="default"):
    try:
        # Importing our flow inside the task to avoid circular import
        return embed_slack_channels_flow(channel_list, upload_by)
    except Exception as e:
        logger.error("Slack channel embedding task failed", exc_info=True)
        raise self.retry(exc=e)