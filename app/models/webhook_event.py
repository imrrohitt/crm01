"""Raw inbound provider events. (provider, provider_event_id) deduplicates retries."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import BaseModel
from app.models.concerns.standard_columns import JSONType, StandardColumns, uuid_pk


class WebhookEvent(StandardColumns, BaseModel):
    __tablename__ = "webhook_events"
    __table_args__ = (UniqueConstraint("provider", "provider_event_id", name="uq_webhook_events_provider_event"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(Text, nullable=False, default="meta")
    provider_event_id: Mapped[str] = mapped_column(Text, nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("tenants.id"), nullable=True)
    social_account_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("social_accounts.id"), nullable=True)
    event_type: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="received")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
