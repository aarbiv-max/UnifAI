from global_utils.celery_app import CeleryApp
from providers.docs import embed_docs_flow
from shared.logger import logger

@CeleryApp().app.task(bind=True, max_retries=5, default_retry_delay=60)
def embed_docs_task(self, doc_list, upload_by="default"):
    try:
        return embed_docs_flow(doc_list, upload_by)
    except Exception as e:
        logger.error("Doc embedding task failed", exc_info=True)
        raise self.retry(exc=e)