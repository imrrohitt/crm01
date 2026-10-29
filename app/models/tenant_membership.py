"""User <-> tenant link. Roles hang off the membership, never off the user."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel
from app.models.concerns.standard_columns import StandardColumns, uuid_pk
from app.models.tenant import Tenant
from app.models.user import User


class Permission(StandardColumns, BaseModel):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class RolePermission(StandardColumns, BaseModel):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("permissions.id"), primary_key=True)


class Role(StandardColumns, BaseModel):
    """tenant_id NULL = system role (owner, admin, manager, agent, viewer)."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tenants.id"))
    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(nullable=False, default=False)

    permissions: Mapped[list[Permission]] = relationship(secondary="role_permissions", viewonly=True)


class MembershipRole(StandardColumns, BaseModel):
    __tablename__ = "membership_roles"

    membership_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenant_memberships.id"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("roles.id"), primary_key=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class TenantMembership(StandardColumns, BaseModel):
    __tablename__ = "tenant_memberships"

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="invited")
    job_title: Mapped[str | None] = mapped_column(Text)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tenant: Mapped[Tenant] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")
    roles: Mapped[list[Role]] = relationship(secondary="membership_roles", viewonly=True)

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def role_codes(self) -> list[str]:
        return sorted(r.code for r in self.roles)
