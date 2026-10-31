"""
Celery application instance and configuration.
"""

import os
import pkgutil

from celery import Celery
from celery.schedules import crontab

from config.settings import get_settings, CELERY_BEAT_SCHEDULE

settings = get_settings()


def _discover_job_modules() -> list[str]:
    """Import every module in app/jobs so the worker registers its tasks."""
    jobs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "jobs")
    return [
        f"app.jobs.{m.name}"
        for m in pkgutil.iter_modules([jobs_dir])
        if m.name != "base_job"
    ]


celery_app = Celery(
    "myapp",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=_discover_job_modules(),  # every module in app/jobs is auto-registered
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_default_queue="default",
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "mailers": {"exchange": "mailers", "routing_key": "mailers"},
        "critical": {"exchange": "critical", "routing_key": "critical"},
        "low_priority": {"exchange": "low_priority", "routing_key": "low_priority"},
    },
)

# Celery Beat: convert hour/minute dict to crontab (empty for framework)
beat_schedule = {}
if CELERY_BEAT_SCHEDULE:
    for name, entry in CELERY_BEAT_SCHEDULE.items():
        s = entry.get("schedule", {})
        beat_schedule[name] = {
            "task": entry["task"],
            "schedule": crontab(hour=s.get("hour", 2), minute=s.get("minute", 0)),
            "options": entry.get("options", {}),
        }
celery_app.conf.beat_schedule = beat_schedule


def _register_job_tasks() -> None:
    """Bind job classes to Celery after the app exists. Retries only network failures."""
    from app.jobs.instagram_send_job import InstagramSendJob
    from app.jobs.instagram_sync_job import InstagramSyncJob
    from app.services.instagram_client import InstagramApiError

    @celery_app.task(bind=True, max_retries=3, queue="default", name="app.jobs.instagram_sync_job.InstagramSyncJob.run")
    def _instagram_sync(self, **kwargs):
        try:
            return InstagramSyncJob().perform(**kwargs)
        except InstagramApiError as exc:
            text = (exc.message or "").lower()
            if "access token" in text or "session has expired" in text:
                raise
            raise self.retry(exc=exc, countdown=InstagramSyncJob.retry_delay) from exc

    @celery_app.task(bind=True, max_retries=3, queue="default", name="app.jobs.instagram_send_job.InstagramSendJob.run")
    def _instagram_send(self, **kwargs):
        try:
            return InstagramSendJob().perform(**kwargs)
        except InstagramApiError as exc:
            if self.request.retries < InstagramSendJob.retry_limit:
                raise self.retry(exc=exc, countdown=InstagramSendJob.retry_delay) from exc
            from uuid import UUID

            from config.database import SessionLocal
            from app.services.instagram_sync_service import InstagramSyncService

            db = SessionLocal()
            try:
                InstagramSyncService(db).fail_send(UUID(str(kwargs.get("message_id"))), exc.message)
            finally:
                db.close()
            return {"status": "failed"}


_register_job_tasks()
