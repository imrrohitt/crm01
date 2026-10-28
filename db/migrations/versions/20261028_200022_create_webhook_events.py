"""
Create webhook_events.

Raw inbound events; the unique key deduplicates Meta retries.

Revision: 20261028_200022
"""

from alembic import op

revision = "20261028_200022"
down_revision = '20261028_200021'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL DEFAULT 'meta',
    provider_event_id TEXT NOT NULL,
    tenant_id UUID,
    social_account_id UUID,
    event_type TEXT,
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'received',
    attempts INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_webhook_events_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE SET NULL,
    CONSTRAINT fk_webhook_events_social_account FOREIGN KEY (social_account_id) REFERENCES social_accounts (id) ON DELETE SET NULL,
    CONSTRAINT uq_webhook_events_provider_event UNIQUE (provider, provider_event_id),
    CONSTRAINT ck_webhook_events_status CHECK (status IN ('received','processing','processed','failed','ignored'))
)"""
    )

    op.execute(
        """CREATE INDEX ix_webhook_events_pending ON webhook_events (received_at) WHERE status IN ('received','failed')"""
    )

    op.execute(
        """CREATE INDEX ix_webhook_events_tenant_received ON webhook_events (tenant_id, received_at DESC)"""
    )

    op.execute(
        """CREATE INDEX ix_webhook_events_payload ON webhook_events USING GIN (payload jsonb_path_ops)"""
    )

    op.execute(
        """CREATE INDEX ix_webhook_events_additional_attributes ON webhook_events USING GIN (additional_attributes jsonb_path_ops)"""
    )

    op.execute(
        """CREATE TRIGGER trg_webhook_events_set_updated_at BEFORE UPDATE ON webhook_events
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS webhook_events")
