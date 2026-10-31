"""
Import Instagram contacts and conversations off the request thread.
The Celery task is registered in config/celery.py so this module can load with the app.
"""

from app.jobs.base_job import BaseJob


class InstagramSyncJob(BaseJob):
    queue = "default"

    def perform(self, connection_id: str, **kwargs) -> dict:
        from uuid import UUID

        from config.database import SessionLocal
        from app.services.instagram_sync_service import InstagramSyncService

        db = SessionLocal()
        try:
            return InstagramSyncService(db).run(UUID(connection_id))
        finally:
            db.close()
