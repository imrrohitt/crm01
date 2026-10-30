"""
Channels (Instagram, ...) for a company: list, connect, disconnect, and the OAuth callback.
"""

import json
import uuid
from urllib.parse import urlencode

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse

from app.controllers.base_controller import BaseController, before_action
from app.controllers.concerns.authenticatable import Authenticatable
from app.controllers.concerns.tenant_scoped import TenantScoped
from app.models import InstagramConnection
from app.services.instagram_service import ConnectError, InstagramService
from config.settings import get_settings

MANAGE_PERMISSION = "settings.manage"


class ChannelsController(Authenticatable, TenantScoped, BaseController):
    @before_action(only=["index", "connect_instagram", "verify_instagram", "preview_instagram_webhook", "disconnect_instagram"])
    def require_login(self) -> None:
        self.authenticate_user()
        self.load_membership()

    def index(self) -> JSONResponse:
        """GET /companies/{company_id}/channels"""
        summary = InstagramService(self.db).channel_summary(self.membership.tenant_id)
        return self.render_json({"channels": [summary], "can_manage": MANAGE_PERMISSION in self.permission_codes()})

    def verify_instagram(self) -> JSONResponse:
        """POST /companies/{company_id}/channels/instagram/verify {instagram_app_id, access_token}"""
        self.require_permission(MANAGE_PERMISSION)
        try:
            profile = InstagramService(self.db).verify_account(
                str(self.params.get("instagram_app_id") or ""),
                str(self.params.get("access_token") or ""),
            )
        except ConnectError as e:
            return self.render_error(e.message, e.status)
        return self.render_json(profile)

    def preview_instagram_webhook(self) -> JSONResponse:
        """POST /companies/{company_id}/channels/instagram/webhook-preview {instagram_app_id}"""
        self.require_permission(MANAGE_PERMISSION)
        try:
            preview = InstagramService(self.db).issue_webhook(self.membership.tenant_id, str(self.params.get("instagram_app_id") or ""))
        except ConnectError as e:
            return self.render_error(e.message, e.status)
        return self.render_json(preview)

    def connect_instagram(self) -> JSONResponse:
        """POST /companies/{company_id}/channels/instagram/connect {instagram_app_id, access_token, id?, webhook_verify_token?}"""
        self.require_permission(MANAGE_PERMISSION)
        try:
            connection = InstagramService(self.db).save_manual_connection(
                uuid.UUID(self._user_id()),
                self.membership.tenant_id,
                str(self.params.get("instagram_app_id") or ""),
                str(self.params.get("access_token") or ""),
                str(self.params.get("id") or "") or None,
                str(self.params.get("webhook_verify_token") or "") or None,
            )
        except ConnectError as e:
            return self.render_error(e.message, e.status)
        return self.render_json(connection.to_public())

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

    def instagram_webhook_verify(self) -> PlainTextResponse:
        """GET /channels/instagram/webhook[/{connection_id}]?hub.mode&hub.verify_token&hub.challenge"""
        q = self.request.query_params
        expected = self._verify_token()
        if q.get("hub.mode") == "subscribe" and expected and q.get("hub.verify_token") == expected and q.get("hub.challenge"):
            return PlainTextResponse(q["hub.challenge"])
        return PlainTextResponse("forbidden", status_code=403)

    async def instagram_webhook(self) -> PlainTextResponse:
        """POST /channels/instagram/webhook[/{connection_id}] — Meta delivers Instagram messaging events here."""
        raw = await self.request.body()
        try:
            payload = json.loads(raw.decode() or "null")
        except ValueError:
            payload = None
        if not isinstance(payload, dict):
            return PlainTextResponse("EVENT_RECEIVED")
        service = InstagramService(self.db)
        if not service.signature_ok(raw, self.request.headers.get("x-hub-signature-256")):
            return PlainTextResponse("invalid signature", status_code=403)
        service.record_webhook(raw, payload, self._connection())
        return PlainTextResponse("EVENT_RECEIVED")

    def _connection(self) -> InstagramConnection | None:
        raw_id = self.params.get("connection_id")
        if not raw_id:
            return None
        try:
            connection_id = raw_id if isinstance(raw_id, uuid.UUID) else uuid.UUID(str(raw_id))
        except ValueError:
            return None
        connection = self.db.get(InstagramConnection, connection_id)
        if connection is None or connection.status == "disconnected":
            return None
        return connection

    def _verify_token(self) -> str:
        if self.params.get("connection_id"):
            connection = self._connection()
            return connection.webhook_verify_token if connection else ""
        return get_settings().INSTAGRAM_VERIFY_TOKEN

    @staticmethod
    def _dest(frontend: str, company_id: uuid.UUID | None, params: dict[str, str]) -> str:
        path = f"/accounts/companies/{company_id}/channels" if company_id else "/accounts/companies"
        return f"{frontend}{path}?{urlencode(params)}"
