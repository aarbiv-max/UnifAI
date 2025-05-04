
from backend.celery_app.init import CeleryApp


def send_task(task_name, celery_queue, **kwargs):
    CeleryApp().app.send_task(task_name,
                              kwargs=kwargs,
                              queue=celery_queue)
