"""Login, token issuing and refresh."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.helpers.jwt_helper import JWTHelper
from app.helpers.password_helper import PasswordHelper
from app.models import Tenant, TenantMembership, User
from app.services.base_service import BaseService
from config.settings import get_settings


class AuthError(Exception):
    def __init__(self, message: str, status: int = 401) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class AuthService(BaseService):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def login(self, email: str, password: str) -> dict[str, Any]:
        user = User.find_by(self.db, email=User.normalize_email(email))
        # Always verify (dummy hash when the user is missing) so timing does not reveal valid emails.
        ok = PasswordHelper.verify(password, user.password_hash if user else None)
        if not user or not ok:
            raise AuthError("Invalid email or password")
        if not user.is_active:
            raise AuthError("This account is not active", status=403)
        companies = self.companies_for(user)
        if not companies:
            raise AuthError("You are not a member of any active company", status=403)
        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()
        return self.session_payload(user, companies)

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        try:
            payload = JWTHelper.decode_token(refresh_token)
        except ValueError:
            raise AuthError("Invalid or expired refresh token")
        if payload.get("type") != "refresh":
            raise AuthError("Invalid or expired refresh token")
        user = self.db.get(User, _to_uuid(payload.get("sub")))
        if not user or not user.is_active:
            raise AuthError("Invalid or expired refresh token")
        return self.session_payload(user, self.companies_for(user))

    def companies_for(self, user: User) -> list[dict[str, Any]]:
        """Active tenants the user belongs to, with their role codes."""
        stmt = (
            select(TenantMembership)
            .options(selectinload(TenantMembership.tenant), selectinload(TenantMembership.roles))
            .where(TenantMembership.user_id == user.id, TenantMembership.status == "active")
            .order_by(TenantMembership.created_at)
        )
        out = []
        for m in self.db.execute(stmt).scalars().all():
            if m.tenant.is_active:
                out.append(company_dict(m.tenant, m))
        return out

    def session_payload(self, user: User, companies: list[dict[str, Any]]) -> dict[str, Any]:
        settings = get_settings()
        return {
            "access_token": JWTHelper.create_access_token(user.id, user.email),
            "refresh_token": JWTHelper.create_refresh_token(user.id),
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user_dict(user),
            "companies": companies,
            "default_company_id": companies[0]["id"] if companies else None,
        }


def _to_uuid(value: Any):
    import uuid

    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def user_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.profile.full_name if user.profile else None,
        "avatar_url": user.profile.avatar_url if user.profile else None,
    }


def company_dict(tenant: Tenant, membership: TenantMembership) -> dict[str, Any]:
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "roles": membership.role_codes,
        "job_title": membership.job_title,
    }
