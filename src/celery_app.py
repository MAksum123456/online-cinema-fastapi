from celery import Celery

celery_app = Celery("tasks", broker="redis://localhost:6379", include=["tasks"])

celery_app.conf.beat_schedule = {
    "delete-expired-tokens": {
        "task": "tasks.delete_expired_tokens",
        "schedule": 10.0,
    }
}
