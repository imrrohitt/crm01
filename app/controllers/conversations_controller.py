"""Conversations created when Instagram contacts are synced."""

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.controllers.base_controller import BaseController, before_action
from app.controllers.concerns.authenticatable import Authenticatable
from app.controllers.concerns.tenant_scoped import TenantScoped
from app.services.instagram_sync_service import InstagramSyncService

READ_PERMISSION = "conversations.read"


class ConversationsController(Authenticatable, TenantScoped, BaseController):
    @before_action(only=["index", "show"])
    def require_login(self) -> None:
        self.authenticate_user()
        self.load_membership()

    def index(self) -> JSONResponse:
        """GET /companies/{company_id}/conversations"""
        self.require_permission(READ_PERMISSION)
        return self.render_json(InstagramSyncService(self.db).conversations(self.membership.tenant_id))

    def show(self) -> JSONResponse:
        """GET /companies/{company_id}/conversations/{conversation_id}"""
        self.require_permission(READ_PERMISSION)
        detail = InstagramSyncService(self.db).conversation(self.membership.tenant_id, self.params["conversation_id"])
        if detail is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return self.render_json(detail)
