"""People who message a connected Instagram account. Not CRM users."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKeyConstraint, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import BaseModel
from app.models.concerns.standard_columns import JSONType, StandardColumns, uuid_pk


class Contact(StandardColumns, BaseModel):
    __tablename__ = "contacts"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "social_account_id"], ["social_accounts.tenant_id", "social_accounts.id"], ondelete="CASCADE"),
        UniqueConstraint("social_account_id", "platform_user_id", name="uq_contacts_account_platform_user"),
        UniqueConstraint("tenant_id", "id", name="uq_contacts_tenant_id_id"),
        UniqueConstraint("tenant_id", "social_account_id", "id", name="uq_contacts_tenant_account_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    social_account_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    platform_user_id: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    profile_picture_url: Mapped[str | None] = mapped_column(Text)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_interaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(Text, nullable=False, default="instagram_dm")
    custom_fields: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
