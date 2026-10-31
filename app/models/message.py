"""A single Instagram DM inside a conversation."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import BaseModel
from app.models.concerns.standard_columns import JSONType, StandardColumns, uuid_pk


class Message(StandardColumns, BaseModel):
    __tablename__ = "messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "social_account_id", "conversation_id"],
            ["conversations.tenant_id", "conversations.social_account_id", "conversations.id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(["tenant_id", "sender_contact_id"], ["contacts.tenant_id", "contacts.id"]),
        UniqueConstraint("social_account_id", "external_message_id", name="uq_messages_account_external"),
        UniqueConstraint("tenant_id", "id", name="uq_messages_tenant_id_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    social_account_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    conversation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    external_message_id: Mapped[str | None] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    sender_type: Mapped[str] = mapped_column(Text, nullable=False)
    sender_contact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    sender_membership_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    content: Mapped[str | None] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(Text, nullable=False, default="text")
    media_metadata: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="received")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
