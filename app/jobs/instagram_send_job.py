"""
Send one queued Instagram DM off the request thread.
The Celery task is registered in config/celery.py so this module can load with the app.
"""

from app.jobs.base_job import BaseJob


class InstagramSendJob(BaseJob):
    queue = "default"
    retry_limit = 3
    retry_delay = 15

    def perform(self, message_id: str, **kwargs) -> dict:
        from uuid import UUID

        from config.database import SessionLocal
        from app.services.instagram_sync_service import InstagramSyncService

        db = SessionLocal()
        try:
            return InstagramSyncService(db).deliver(UUID(message_id))
        finally:
            db.close()
