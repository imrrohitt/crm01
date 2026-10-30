"""Instagram credentials a company pasted in, and the webhook issued for that account."""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, LargeBinary, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import BaseModel
from app.models.concerns.standard_columns import StandardColumns, uuid_pk


class InstagramConnection(StandardColumns, BaseModel):
    __tablename__ = "instagram_connections"
    __table_args__ = (
        UniqueConstraint("tenant_id", "instagram_app_id", name="uq_instagram_connections_tenant_app"),
        UniqueConstraint("webhook_verify_token", name="uq_instagram_connections_verify_token"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), nullable=False)
    instagram_app_id: Mapped[str] = mapped_column(Text, nullable=False)
    access_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    webhook_verify_token: Mapped[str] = mapped_column(Text, nullable=False)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="connected")
    connected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))

    def to_public(self) -> dict[str, Any]:
        """Safe for the browser. The access token stays encrypted in the database."""
        attrs = self.additional_attributes or {}
        return {
            "id": self.id,
            "instagram_app_id": self.instagram_app_id,
            "username": attrs.get("username"),
            "name": attrs.get("name"),
            "profile_picture_url": attrs.get("profile_picture_url"),
            "webhook_url": self.webhook_url,
            "webhook_verify_token": self.webhook_verify_token,
            "status": self.status,
            "created_at": self.created_at,
        }
