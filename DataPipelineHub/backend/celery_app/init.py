from config.app_config import AppConfig
from global_utils.celery_app import CeleryApp

config = AppConfig.get_instance()

# Initialize CeleryApp with basic parameters
celery_instance = CeleryApp(
    broker_user_name=config.broker_user_name,
    broker_password=config.broker_password,
    task_modules=["celery_app.tasks.pipeline_tasks"]
)

# Get the celery app
celery = celery_instance.app

# Override/update with custom RabbitMQ stability configurations
celery.conf.update(
    broker_transport_options={
        "heartbeat": config.broker_heartbeat,
        "tcp_user_timeout": config.broker_tcp_user_timeout,
        "socket_keepalive": config.broker_socket_keepalive
    },
    task_acks_late=config.task_acks_late,
    task_reject_on_worker_lost=config.task_reject_on_worker_lost,
    worker_cancel_long_running_tasks_on_connection_loss=config.worker_cancel_long_running_tasks_on_connection_loss
)


# TODO: In order to start celery worker, below line should be triggered from backend/
# For separate workers by source type:
# celery -A celery_app.init worker -c 1 --loglevel=info -Q slack_queue -n slack_worker  
# celery -A celery_app.init worker -c 1 --loglevel=info -Q document_queue -n document_worker