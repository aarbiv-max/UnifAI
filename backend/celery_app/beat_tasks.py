def get_beat_schedule():
    return {
        'fetch-dpr-progress-every-5-mins': {
            'task': 'celery_app.tasks.fetch_dpr_progress',
            'schedule': 300.0
        },
        'fetch-training-progress-every-5-mins': {
            'task': 'celery_app.tasks.fetch_training_progress',
            'schedule': 300.0
        }
    }
