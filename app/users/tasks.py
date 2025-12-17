import time

from app.core.celery_app import celery_app
from app.repositories.celery_user_repo import RedisUserRepositorySync


@celery_app.task
def cleanup_inactive_users():
    repo = RedisUserRepositorySync()
    deleted = repo.delete_inactive_users(
        inactive_since=time.time() - 1 * 24 * 60 * 60
    )  # 1 days
    return deleted
