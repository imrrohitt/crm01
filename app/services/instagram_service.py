"""
Connect / disconnect Instagram accounts for a tenant.

Flow: connect_url() -> user logs in on Instagram -> Instagram redirects to the API callback
with ?code&state -> complete_connection() verifies state, exchanges the code, stores the
account and the encrypted token.
"""

import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.helpers.crypto_helper import KEY_VERSION, CryptoError, CryptoHelper
from app.models import (
    InstagramConnection, Permission, RolePermission, MembershipRole, SocialAccount, SocialAccountToken,
    Tenant, TenantMembership, WebhookEvent,
)
from app.services.base_service import BaseService
from app.services.entitlement_service import EntitlementService
from app.services.instagram_client import InstagramApiError, InstagramClient
from config.settings import get_settings

STATE_TTL_MINUTES = 10
DEFAULT_TOKEN_LIFETIME = 60 * 24 * 3600  # long-lived tokens last 60 days
logger = logging.getLogger(__name__)
_MESSAGE_KEYS = ("message", "postback", "read", "reaction", "referral")


class ConnectError(Exception):
    """User-facing reason a connection could not be completed."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class InstagramService(BaseService):
    def __init__(self, db: Session, client: InstagramClient | None = None) -> None:
        super().__init__(db)
        self.client = client or InstagramClient()

    # --- state (CSRF protection + remembers who/which company started the flow) ---
    @staticmethod
    def make_state(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
        s = get_settings()
        payload = {
            "type": "ig_connect",
            "sub": str(user_id),
            "tid": str(tenant_id),
            "jti": uuid.uuid4().hex,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=STATE_TTL_MINUTES),
        }
        return jwt.encode(payload, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM)

    @staticmethod
    def read_state(state: str) -> tuple[uuid.UUID, uuid.UUID]:
        s = get_settings()
        try:
            p = jwt.decode(state, s.JWT_SECRET_KEY, algorithms=[s.JWT_ALGORITHM])
            if p.get("type") != "ig_connect":
                raise ValueError
            return uuid.UUID(p["sub"]), uuid.UUID(p["tid"])
        except (JWTError, ValueError, KeyError):
            raise ConnectError("This connection link expired or is invalid. Please try again.")

    # --- start ---
    def connect_url(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
        if not self.client.configured:
            raise ConnectError("Instagram is not configured on the server yet.", status=503)
        return self.client.authorize_url(self.make_state(user_id, tenant_id))

    def verify_account(self, app_id: str, access_token: str) -> dict[str, Any]:
        """Confirm the access token can read this Instagram professional account."""
        app_id, access_token = app_id.strip(), access_token.strip()
        if not app_id or not access_token:
            raise ConnectError("Enter the Instagram app id and access token.")
        try:
            profile = self.client.business_profile(app_id, access_token)
        except InstagramApiError as e:
            raise ConnectError(e.message or "Instagram could not load this account.") from e
        if str(profile.get("id") or "") != app_id:
            raise ConnectError("This access token does not belong to that Instagram account.")
        return {
            "id": app_id,
            "username": profile.get("username"),
            "name": profile.get("name"),
            "profile_picture_url": profile.get("profile_picture_url"),
        }

    def issue_webhook(self, tenant_id: uuid.UUID, app_id: str) -> dict[str, str]:
        """Webhook URL and verify token for this Instagram id. Nothing is saved until submit."""
        app_id = app_id.strip()
        if not app_id:
            raise ConnectError("Enter the Instagram app id.")
        base = self.public_base()
        if not base:
            raise ConnectError("A public webhook URL is not configured on the server yet.", status=503)
        existing = self.db.execute(
            select(InstagramConnection).where(
                InstagramConnection.tenant_id == tenant_id, InstagramConnection.instagram_app_id == app_id
            )
        ).scalars().first()
        connection_id = existing.id if existing else uuid.uuid4()
        verify_token = existing.webhook_verify_token if existing else secrets.token_urlsafe(32)
        return {
            "id": str(connection_id),
            "webhook_verify_token": verify_token,
            "webhook_url": f"{base}/api/v1/channels/instagram/webhook/{connection_id}",
        }

    def save_manual_connection(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        app_id: str,
        access_token: str,
        connection_id: str | None = None,
        webhook_verify_token: str | None = None,
    ) -> InstagramConnection:
        """Store a pasted Instagram app id and access token, and issue a webhook for it."""
        app_id, access_token = app_id.strip(), access_token.strip()
        if not app_id or not access_token:
            raise ConnectError("Enter the Instagram app id and access token.")
        base = self.public_base()
        if not base:
            raise ConnectError("A public webhook URL is not configured on the server yet.", status=503)
        profile = self.verify_account(app_id, access_token)

        rows = list(self.db.execute(
            select(InstagramConnection).where(InstagramConnection.instagram_app_id == app_id)
        ).scalars())
        existing = next((row for row in rows if row.tenant_id == tenant_id), None)
        if any(row.tenant_id != tenant_id and row.status != "disconnected" for row in rows):
            raise ConnectError("This Instagram account is already connected to another company.", status=409)
        if existing is None or existing.status == "disconnected":
            self._check_limit(tenant_id)

        try:
            encrypted = CryptoHelper.encrypt(access_token)
        except CryptoError as e:
            raise ConnectError(e.args[0] if e.args else "Could not store the access token.", status=503) from e

        issued_id = self._issued_id(connection_id)
        issued_token = (webhook_verify_token or "").strip()
        if existing is None:
            if issued_id and self.db.get(InstagramConnection, issued_id) is not None:
                raise ConnectError("Generate the webhook again.")
            connection = InstagramConnection(
                id=issued_id or uuid.uuid4(),
                tenant_id=tenant_id,
                instagram_app_id=app_id,
                access_token_encrypted=encrypted,
                key_version=KEY_VERSION,
                webhook_verify_token=issued_token or secrets.token_urlsafe(32),
                webhook_url="",
                status="connected",
                connected_by_user_id=user_id,
            )
            self.db.add(connection)
            self.db.flush()
        else:
            connection = existing
            connection.access_token_encrypted = encrypted
            connection.key_version = KEY_VERSION
            connection.status = "connected"
            connection.connected_by_user_id = user_id
            if issued_token:
                connection.webhook_verify_token = issued_token
        connection.webhook_url = f"{base}/api/v1/channels/instagram/webhook/{connection.id}"
        attrs = dict(connection.additional_attributes or {})
        attrs.update({"username": profile.get("username"), "name": profile.get("name"), "profile_picture_url": profile.get("profile_picture_url")})
        connection.additional_attributes = attrs
        self.db.commit()
        self.db.refresh(connection)
        return connection

    @staticmethod
    def _issued_id(connection_id: str | None) -> uuid.UUID | None:
        if not connection_id:
            return None
        try:
            return uuid.UUID(str(connection_id))
        except ValueError:
            raise ConnectError("Generate the webhook again.")

    @staticmethod
    def public_base() -> str:
        """Origin of INSTAGRAM_REDIRECT_URI, which is the public https host (ngrok in development)."""
        parts = urlsplit(get_settings().INSTAGRAM_REDIRECT_URI.strip())
        if not parts.scheme or not parts.netloc:
            return ""
        return f"{parts.scheme}://{parts.netloc}"

    # --- finish ---
    def complete_connection(self, code: str, state: str) -> SocialAccount:
        """Returns the saved account. state must have been issued by connect_url()."""
        user_id, tenant_id = self.read_state(state)
        self._assert_can_manage(user_id, tenant_id)
        code = code.split("#")[0]  # Instagram appends "#_" to the code
        try:
            short = self.client.exchange_code(code)
            short_token = short["access_token"]
            try:
                long = self.client.long_lived_token(short_token)
            except InstagramApiError:
                long = {}  # fall back to the short-lived token rather than failing the connect
            access_token = long.get("access_token") or short_token
            expires_in = int(long.get("expires_in") or DEFAULT_TOKEN_LIFETIME)
            me = self.client.profile(access_token)
        except (InstagramApiError, KeyError) as e:
            raise ConnectError(getattr(e, "message", "Instagram did not return the expected data."))

        platform_id = str(me.get("user_id") or short.get("user_id") or "")
        if not platform_id:
            raise ConnectError("Instagram did not return an account id.")

        account = self.db.execute(
            select(SocialAccount).where(SocialAccount.platform == "instagram", SocialAccount.platform_account_id == platform_id)
        ).scalars().first()

        if account and account.tenant_id != tenant_id:
            raise ConnectError("This Instagram account is already connected to another company.")
        if account is None:
            self._check_limit(tenant_id)
            account = SocialAccount(tenant_id=tenant_id, platform="instagram", platform_account_id=platform_id)
            self.db.add(account)

        account.username = me.get("username")
        account.account_type = me.get("account_type")
        account.status = "connected"
        account.connected_by_user_id = user_id
        account.connected_at = datetime.now(timezone.utc)
        account.disconnected_at = None
        attrs = dict(account.additional_attributes or {})
        attrs.update({"name": me.get("name"), "profile_picture_url": me.get("profile_picture_url")})
        account.additional_attributes = attrs
        self.db.flush()

        scopes = short.get("permissions") or get_settings().INSTAGRAM_SCOPES
        if isinstance(scopes, str):
            scopes = [x.strip() for x in scopes.split(",") if x.strip()]
        token = account.token or SocialAccountToken(social_account_id=account.id)
        token.access_token_encrypted = CryptoHelper.encrypt(access_token)
        token.key_version = KEY_VERSION
        token.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        token.scopes = list(scopes)
        self.db.add(token)
        self.db.commit()
        self.db.refresh(account)
        return account

    def _assert_can_manage(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        """The state was issued earlier; re-check the user is still an active member who may connect channels."""
        stmt = (
            select(func.count())
            .select_from(TenantMembership)
            .join(Tenant, Tenant.id == TenantMembership.tenant_id)
            .join(MembershipRole, MembershipRole.membership_id == TenantMembership.id)
            .join(RolePermission, RolePermission.role_id == MembershipRole.role_id)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(
                TenantMembership.tenant_id == tenant_id,
                TenantMembership.user_id == user_id,
                TenantMembership.status == "active",
                Tenant.status == "active",
                Permission.code == "settings.manage",
            )
        )
        if not self.db.execute(stmt).scalar():
            raise ConnectError("You no longer have permission to connect channels for this company.")

    def _check_limit(self, tenant_id: uuid.UUID) -> None:
        limit = EntitlementService(self.db).features(tenant_id).get("instagram_accounts")
        if not isinstance(limit, int) or isinstance(limit, bool):
            return
        if self._used_instagram_slots(tenant_id) >= limit:
            raise ConnectError(f"Your plan allows {limit} Instagram account(s). Disconnect one or upgrade your plan.")

    def _used_instagram_slots(self, tenant_id: uuid.UUID) -> int:
        social = self.db.execute(
            select(func.count()).select_from(SocialAccount).where(
                SocialAccount.tenant_id == tenant_id, SocialAccount.platform == "instagram", SocialAccount.status != "disconnected"
            )
        ).scalar() or 0
        manual = self.db.execute(
            select(func.count()).select_from(InstagramConnection).where(
                InstagramConnection.tenant_id == tenant_id, InstagramConnection.status != "disconnected"
            )
        ).scalar() or 0
        return int(social) + int(manual)

    # --- list / disconnect ---
    def accounts(self, tenant_id: uuid.UUID) -> list[SocialAccount]:
        stmt = select(SocialAccount).where(SocialAccount.tenant_id == tenant_id, SocialAccount.platform == "instagram").order_by(SocialAccount.connected_at)
        return list(self.db.execute(stmt).scalars().all())

    def connections(self, tenant_id: uuid.UUID) -> list[InstagramConnection]:
        stmt = select(InstagramConnection).where(
            InstagramConnection.tenant_id == tenant_id, InstagramConnection.status != "disconnected"
        ).order_by(InstagramConnection.created_at)
        return list(self.db.execute(stmt).scalars().all())

    def disconnect(self, tenant_id: uuid.UUID, account_id: uuid.UUID) -> SocialAccount | InstagramConnection | None:
        connection = self.db.get(InstagramConnection, account_id)
        if connection is not None:
            if connection.tenant_id != tenant_id:
                return None
            connection.status = "disconnected"
            self.db.commit()
            self.db.refresh(connection)
            return connection
        account = self.db.get(SocialAccount, account_id)
        if account is None or account.tenant_id != tenant_id:
            return None
        if account.token is not None:
            self.db.delete(account.token)
        account.status = "disconnected"
        account.disconnected_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(account)
        return account

    def channel_summary(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        limit = EntitlementService(self.db).features(tenant_id).get("instagram_accounts")
        accounts = [a for a in self.accounts(tenant_id)]
        return {
            "key": "instagram",
            "name": "Instagram",
            "configured": bool(self.public_base()),
            "limit": limit if isinstance(limit, int) and not isinstance(limit, bool) else None,
            "accounts": [a.to_public() for a in accounts],
            "connections": [c.to_public() for c in self.connections(tenant_id)],
        }

    # --- webhooks (Meta calls these; no logged-in user) ---
    def signature_ok(self, raw: bytes, header: str | None) -> bool:
        """X-Hub-Signature-256 is checked only when an app secret is configured."""
        secret = get_settings().INSTAGRAM_APP_SECRET
        if not secret:
            return True
        if not header or not header.startswith("sha256="):
            return False
        digest = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        return hmac.compare_digest(header.removeprefix("sha256="), digest)

    def record_webhook(self, raw: bytes, payload: dict[str, Any], connection: InstagramConnection | None = None) -> None:
        """Store one inbound delivery. A Meta retry of the same body is ignored."""
        event_id = hashlib.sha256(raw).hexdigest()
        already = self.db.execute(
            select(WebhookEvent.id).where(WebhookEvent.provider == "meta", WebhookEvent.provider_event_id == event_id)
        ).first()
        if already:
            return
        account = self._account_for_payload(payload)
        self._log_messages(payload)
        tenant_id = account.tenant_id if account else (connection.tenant_id if connection else None)
        self.db.add(
            WebhookEvent(
                provider="meta",
                provider_event_id=event_id,
                tenant_id=tenant_id,
                social_account_id=account.id if account else None,
                event_type=self._event_type(payload),
                payload=payload,
                status="received",
                additional_attributes={"instagram_connection_id": str(connection.id)} if connection else {},
            )
        )
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()

    def _account_for_payload(self, payload: dict[str, Any]) -> SocialAccount | None:
        for entry in payload.get("entry") or []:
            if not isinstance(entry, dict) or not entry.get("id"):
                continue
            account = self.db.execute(
                select(SocialAccount).where(
                    SocialAccount.platform == "instagram",
                    SocialAccount.platform_account_id == str(entry["id"]),
                )
            ).scalars().first()
            if account:
                return account
        return None

    @staticmethod
    def _event_type(payload: dict[str, Any]) -> str:
        for entry in payload.get("entry") or []:
            if not isinstance(entry, dict):
                continue
            for item in entry.get("messaging") or []:
                if not isinstance(item, dict):
                    continue
                for key in _MESSAGE_KEYS:
                    if key in item:
                        return key
        return str(payload.get("object") or "instagram")

    @staticmethod
    def _log_messages(payload: dict[str, Any]) -> None:
        for entry in payload.get("entry") or []:
            if not isinstance(entry, dict):
                continue
            for item in entry.get("messaging") or []:
                if not isinstance(item, dict):
                    continue
                message = item.get("message") or {}
                text = message.get("text") if isinstance(message, dict) else None
                sender = (item.get("sender") or {}).get("id")
                logger.info("instagram webhook entry=%s from=%s text=%s", entry.get("id"), sender, text)
