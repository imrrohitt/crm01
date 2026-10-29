"""Tenant = one influencer / company."""

import uuid

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel
from app.models.concerns.standard_columns import StandardColumns, uuid_pk


class Tenant(StandardColumns, BaseModel):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="UTC")

    memberships: Mapped[list["TenantMembership"]] = relationship(back_populates="tenant")  # noqa: F821
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="tenant")  # noqa: F821

    @property
    def is_active(self) -> bool:
        return self.status == "active"
