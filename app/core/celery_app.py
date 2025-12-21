# celery config file
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "project_fast",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.autodiscover_tasks(["app.users"])
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
)
