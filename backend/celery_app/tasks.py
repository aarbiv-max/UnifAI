import logging
from celery_app.init import CeleryApp
from providers.dpr import celery_check_dpr_progress
from providers.training import check_training_progress

@CeleryApp().app.task(bind=True, max_retries=16, default_retry_delay=30)
def fetch_dpr_progress(self):
    """
    Celery task for the metrics fetch of dpr processes.
    """
    try:
        celery_check_dpr_progress()
    except Exception as e:
        logging.error("DPR task failed.", exc_info=True)
        raise self.retry(exc=e)
    
@CeleryApp().app.task(bind=True, max_retries=16, default_retry_delay=30)
def fetch_training_progress(self):
    """
    Celery task for uninstalling the training pod.
    """
    try:
        check_training_progress()
    except Exception as e:
        logging.error("training task failed.", exc_info=True)
        raise self.retry(exc=e)
