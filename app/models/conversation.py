"""One thread between a contact and a connected Instagram account."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import BaseModel
from app.models.concerns.standard_columns import StandardColumns, uuid_pk


class Conversation(StandardColumns, BaseModel):
    __tablename__ = "conversations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "social_account_id", "contact_id"],
            ["contacts.tenant_id", "contacts.social_account_id", "contacts.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("tenant_id", "id", name="uq_conversations_tenant_id_id"),
        UniqueConstraint("tenant_id", "social_account_id", "id", name="uq_conversations_tenant_account_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    social_account_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    external_conversation_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    priority: Mapped[str] = mapped_column(Text, nullable=False, default="normal")
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
