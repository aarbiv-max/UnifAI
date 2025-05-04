"""
Module for importing non-configured flask extensions
"""
from celery import Celery
from prompt_lab.utils.util import get_mongo_url, get_rabbitmq_url
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
            'celery_promp_lab',
            broker=get_rabbitmq_url(),
            BROKER_USER='genie',
            BROKER_PASSWORD='genie123',
            backend=get_mongo_url(),
            include=['prompt_lab.celery_app.tasks']  # Fully qualified path
        )

        # Configure Celery logging to use the application's logger
        self.celery_app.conf.update(
            task_acks_late=True,  # Acknowledge only after task completion
            task_reject_on_worker_lost=True,  # Requeue tasks if the worker crashes
            worker_hijack_root_logger=False,  # Prevent Celery from hijacking the root logger
            worker_log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            worker_task_log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )

        # Set the Celery logger to use the custom logger
        celery_logger = logging.getLogger('celery')
        celery_logger.handlers = logger.handlers
        celery_logger.setLevel(logger.level)

    @property
    def app(self):
        """Get the singleton Celery instance."""
        return self.celery_app