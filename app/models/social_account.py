"""Connected social (Instagram) accounts and their encrypted tokens."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, LargeBinary, String, Text, Uuid
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel
from app.models.concerns.standard_columns import StandardColumns, uuid_pk

ScopesType = ARRAY(Text).with_variant(JSON(), "sqlite")


class SocialAccount(StandardColumns, BaseModel):
    __tablename__ = "social_accounts"

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), nullable=False)
    platform: Mapped[str] = mapped_column(Text, nullable=False, default="instagram")
    platform_account_id: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[str | None] = mapped_column(Text)
    account_type: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, nullable=False, default="connected")
    connected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    token: Mapped["SocialAccountToken | None"] = relationship(back_populates="social_account", uselist=False)

    def to_public(self) -> dict[str, Any]:
        """Safe to return to the browser: never includes token data."""
        attrs = self.additional_attributes or {}
        return {
            "id": self.id,
            "platform": self.platform,
            "platform_account_id": self.platform_account_id,
            "username": self.username,
            "account_type": self.account_type,
            "status": self.status,
            "profile_picture_url": attrs.get("profile_picture_url"),
            "connected_at": self.connected_at,
        }


class SocialAccountToken(StandardColumns, BaseModel):
    __tablename__ = "social_account_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    social_account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("social_accounts.id"), nullable=False, unique=True)
    access_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    refresh_token_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[list[str]] = mapped_column(ScopesType, nullable=False, default=list)

    social_account: Mapped[SocialAccount] = relationship(back_populates="token")
