"""
Connect / disconnect Instagram accounts for a tenant.

Flow: connect_url() -> user logs in on Instagram -> Instagram redirects to the API callback
with ?code&state -> complete_connection() verifies state, exchanges the code, stores the
account and the encrypted token.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.helpers.crypto_helper import KEY_VERSION, CryptoHelper
from app.models import Permission, RolePermission, MembershipRole, SocialAccount, SocialAccountToken, Tenant, TenantMembership
from app.services.base_service import BaseService
from app.services.entitlement_service import EntitlementService
from app.services.instagram_client import InstagramApiError, InstagramClient
from config.settings import get_settings

STATE_TTL_MINUTES = 10
DEFAULT_TOKEN_LIFETIME = 60 * 24 * 3600  # long-lived tokens last 60 days


class ConnectError(Exception):
    """User-facing reason a connection could not be completed."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


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
            raise ConnectError("Instagram is not configured on the server yet.")
        return self.client.authorize_url(self.make_state(user_id, tenant_id))

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
        used = self.db.execute(
            select(func.count()).select_from(SocialAccount).where(
                SocialAccount.tenant_id == tenant_id, SocialAccount.platform == "instagram", SocialAccount.status != "disconnected"
            )
        ).scalar() or 0
        if used >= limit:
            raise ConnectError(f"Your plan allows {limit} Instagram account(s). Disconnect one or upgrade your plan.")

    # --- list / disconnect ---
    def accounts(self, tenant_id: uuid.UUID) -> list[SocialAccount]:
        stmt = select(SocialAccount).where(SocialAccount.tenant_id == tenant_id, SocialAccount.platform == "instagram").order_by(SocialAccount.connected_at)
        return list(self.db.execute(stmt).scalars().all())

    def disconnect(self, tenant_id: uuid.UUID, account_id: uuid.UUID) -> SocialAccount | None:
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
            "configured": self.client.configured,
            "limit": limit if isinstance(limit, int) and not isinstance(limit, bool) else None,
            "accounts": [a.to_public() for a in accounts],
        }
