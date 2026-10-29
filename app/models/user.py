"""Global login identity. A user can belong to many tenants through TenantMembership."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.helpers.password_helper import PasswordHelper
from app.models.base_model import BaseModel
from app.models.concerns.standard_columns import StandardColumns, uuid_pk

if TYPE_CHECKING:
    from app.models.tenant_membership import TenantMembership


class User(StandardColumns, BaseModel):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False)
    memberships: Mapped[list["TenantMembership"]] = relationship(back_populates="user")

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    def set_password(self, password: str) -> None:
        self.password_hash = PasswordHelper.hash(password)

    def check_password(self, password: str) -> bool:
        return PasswordHelper.verify(password, self.password_hash)

    @property
    def is_active(self) -> bool:
        return self.status == "active"


class UserProfile(StandardColumns, BaseModel):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    locale: Mapped[str] = mapped_column(Text, nullable=False, default="en")
    timezone: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="profile")
