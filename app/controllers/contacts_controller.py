"""Contacts synced from a connected Instagram account."""

import uuid

from fastapi.responses import JSONResponse

from app.controllers.base_controller import BaseController, before_action
from app.controllers.concerns.authenticatable import Authenticatable
from app.controllers.concerns.tenant_scoped import TenantScoped
from app.jobs.instagram_sync_job import InstagramSyncJob
from app.services.instagram_service import ConnectError
from app.services.instagram_sync_service import InstagramSyncService

READ_PERMISSION = "contacts.read"
MANAGE_PERMISSION = "settings.manage"


class ContactsController(Authenticatable, TenantScoped, BaseController):
    @before_action(only=["index", "enable_sync"])
    def require_login(self) -> None:
        self.authenticate_user()
        self.load_membership()

    def index(self) -> JSONResponse:
        """GET /companies/{company_id}/contacts"""
        self.require_permission(READ_PERMISSION)
        service = InstagramSyncService(self.db)
        tenant_id = self.membership.tenant_id
        return self.render_json({"accounts": service.accounts(tenant_id), "contacts": service.contacts(tenant_id)})

    def enable_sync(self) -> JSONResponse:
        """POST /companies/{company_id}/contacts/instagram/{connection_id}/sync — enqueue the import."""
        self.require_permission(MANAGE_PERMISSION)
        service = InstagramSyncService(self.db)
        try:
            state = service.enable(self.membership.tenant_id, self.params["connection_id"], uuid.UUID(self._user_id()))
        except ConnectError as exc:
            return self.render_error(exc.message, exc.status)
        InstagramSyncJob.perform_later(connection_id=str(state["id"]))
        return self.render_json(state)
