"""
Channels (Instagram, ...) for a company: list, connect, disconnect, and the OAuth callback.
"""

import uuid
from urllib.parse import urlencode

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, RedirectResponse

from app.controllers.base_controller import BaseController, before_action
from app.controllers.concerns.authenticatable import Authenticatable
from app.controllers.concerns.tenant_scoped import TenantScoped
from app.services.instagram_service import ConnectError, InstagramService
from config.settings import get_settings

MANAGE_PERMISSION = "settings.manage"


class ChannelsController(Authenticatable, TenantScoped, BaseController):
    @before_action(only=["index", "connect_instagram", "disconnect_instagram"])
    def require_login(self) -> None:
        self.authenticate_user()
        self.load_membership()

    def index(self) -> JSONResponse:
        """GET /companies/{company_id}/channels"""
        summary = InstagramService(self.db).channel_summary(self.membership.tenant_id)
        return self.render_json({"channels": [summary], "can_manage": MANAGE_PERMISSION in self.permission_codes()})

    def connect_instagram(self) -> JSONResponse:
        """POST /companies/{company_id}/channels/instagram/connect -> {authorize_url}"""
        self.require_permission(MANAGE_PERMISSION)
        try:
            url = InstagramService(self.db).connect_url(uuid.UUID(self._user_id()), self.membership.tenant_id)
        except ConnectError as e:
            return self.render_error(e.message, 503)
        return self.render_json({"authorize_url": url})

    def disconnect_instagram(self) -> JSONResponse:
        """DELETE /companies/{company_id}/channels/instagram/{account_id}"""
        self.require_permission(MANAGE_PERMISSION)
        account = InstagramService(self.db).disconnect(self.membership.tenant_id, self.params["account_id"])
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")
        return self.render_json(account.to_public())

    async def instagram_callback(self):
        """
        GET /channels/instagram/callback?code&state  (Instagram redirects the browser here).
        No Bearer token: the signed `state` identifies the user and company. Always ends with
        a redirect back to the web app.
        """
        q = self.request.query_params
        frontend = get_settings().FRONTEND_URL.rstrip("/")
        company_id = None
        try:
            if q.get("state"):
                try:  # lets errors (e.g. user pressed Cancel on Instagram) land on the right company
                    company_id = InstagramService.read_state(q["state"])[1]
                except ConnectError:
                    pass
            if q.get("error"):
                raise ConnectError(q.get("error_description") or "Instagram connection was cancelled.")
            code, state = q.get("code"), q.get("state")
            if not code or not state:
                raise ConnectError("Instagram did not return the expected data. Please try again.")
            InstagramService.read_state(state)
            await run_in_threadpool(self._finish, code, state)
        except ConnectError as e:
            return RedirectResponse(self._dest(frontend, company_id, {"channel_error": e.message}), status_code=302)
        return RedirectResponse(self._dest(frontend, company_id, {"connected": "instagram"}), status_code=302)

    def _finish(self, code: str, state: str) -> None:
        InstagramService(self.db).complete_connection(code, state)

    @staticmethod
    def _dest(frontend: str, company_id: uuid.UUID | None, params: dict[str, str]) -> str:
        path = f"/accounts/companies/{company_id}/channels" if company_id else "/accounts/companies"
        return f"{frontend}{path}?{urlencode(params)}"
