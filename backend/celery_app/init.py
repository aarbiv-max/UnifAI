"""
Module for importing non-configured flask extensions
"""
from celery import Celery
from prompt_lab.utils.logging_config import logger
import logging


class CeleryApp:
    """
    Singleton class for initializing and configuring Celery.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CeleryApp, cls).__new__(cls)
            cls._instance._initialize_celery()
        return cls._instance

    def _initialize_celery(self):
        """Initialize the Celery instance."""
        self.celery_app = Celery(
            'celery_backend',
            broker=f"amqp://rabbitmq:5672",
            BROKER_USER='genie',
            BROKER_PASSWORD='genie123',
            backend="mongodb://mongodb:27017",
            include=['celery_app.tasks']
        )

        self.celery_app.conf.update(
            task_acks_late=True,  
            task_reject_on_worker_lost=True,
            worker_hijack_root_logger=False, 
            worker_log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            worker_task_log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            beat_schedule={
                'fetch-dpr-progress-every-5-mins': {
                'task': 'celery_app.tasks.fetch_dpr_progress',
                'schedule': 300.0 
            }
    }
        )

        celery_logger = logging.getLogger('celery')
        celery_logger.handlers = logger.handlers
        celery_logger.setLevel(logger.level)

    @property
    def app(self):
        """Get the singleton Celery instance."""
        return self.celery_app

celery = CeleryApp().app