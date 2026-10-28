"""
Create billing_events.

Webhook idempotency: the same provider event can never be inserted twice.

Revision: 20261028_200016
"""

from alembic import op

revision = "20261028_200016"
down_revision = '20261028_200015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE billing_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    subscription_id UUID,
    provider TEXT NOT NULL,
    provider_event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    processed_at TIMESTAMPTZ,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_billing_events_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_billing_events_subscription FOREIGN KEY (tenant_id, subscription_id) REFERENCES subscriptions (tenant_id, id) ON DELETE SET NULL (subscription_id),
    CONSTRAINT uq_billing_events_provider_event UNIQUE (provider, provider_event_id)
)"""
    )

    op.execute(
        """CREATE INDEX ix_billing_events_tenant_created ON billing_events (tenant_id, created_at DESC)"""
    )

    op.execute(
        """CREATE INDEX ix_billing_events_unprocessed ON billing_events (created_at) WHERE processed_at IS NULL"""
    )

    op.execute(
        """CREATE TRIGGER trg_billing_events_set_updated_at BEFORE UPDATE ON billing_events
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS billing_events")
