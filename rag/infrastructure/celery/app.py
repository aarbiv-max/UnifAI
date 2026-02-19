"""Celery app initialization for RAG workers."""
from celery.schedules import crontab
from config.app_config import AppConfig
from global_utils.celery_app import CeleryApp
from datetime import timedelta

config = AppConfig.get_instance()

celery = CeleryApp(
    broker_user_name=config.broker_user_name,
    broker_password=config.broker_password,
    task_modules=[
        "infrastructure.celery.workers.pipeline_tasks",
        "infrastructure.celery.workers.slack_event_tasks",
        "infrastructure.celery.workers.slack_sync_tasks",
        "infrastructure.celery.workers.slack_restriction_tasks",
    ]
).app

# ── Celery Beat schedule ──────────────────────────────────────────────
celery.conf.beat_schedule = {
    "slack-incremental-sync": {
        "task": "infrastructure.celery.workers.slack_sync_tasks.slack_incremental_sync_task",
        "schedule": crontab(minute=0, hour="*/12"),  # twice a day
        "options": {"queue": "slack_queue"},
    },
}

# To start celery beat from rag/:
# celery -A infrastructure.celery.app beat --loglevel=info
#
# To start celery workers from rag/:
# celery -A infrastructure.celery.app worker -c 1 --loglevel=info -Q slack_queue -n slack_worker
# celery -A infrastructure.celery.app worker -c 1 --loglevel=info -Q document_queue -n document_worker

