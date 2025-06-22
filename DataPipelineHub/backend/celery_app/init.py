from config.app_config import AppConfig
from global_utils.celery_app import CeleryApp

config = AppConfig()
celery = CeleryApp(broker_user_name=config.broker_user_name, broker_password=config.broker_password,
                   task_modules=["data_sources.slack.slack_tasks", "data_sources.docs.docs_tasks"]).app

# TODO: In order to start celery worker, below line should be triggered from backend/
# celery -A celery_app.init worker -c 1 --loglevel=info -Q slack_queue -n data_sources
# celery -A celery_app.init worker -c 1 --loglevel=info -Q docs_queue -n data_sources