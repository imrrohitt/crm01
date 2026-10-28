"""
Create subscriptions.

At most one live (trialing/active/past_due) subscription per tenant, enforced by a partial unique index.

Revision: 20261028_200014
"""

from alembic import op

revision = "20261028_200014"
down_revision = '20261028_200013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    plan_id UUID NOT NULL,
    status TEXT NOT NULL DEFAULT 'trialing',
    starts_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    trial_ends_at TIMESTAMPTZ,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT false,
    canceled_at TIMESTAMPTZ,
    provider TEXT,
    provider_subscription_id TEXT,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_subscriptions_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_subscriptions_plan FOREIGN KEY (plan_id) REFERENCES plans (id) ON DELETE RESTRICT,
    CONSTRAINT uq_subscriptions_tenant_id_id UNIQUE (tenant_id, id),
    CONSTRAINT ck_subscriptions_status CHECK (status IN ('trialing','active','past_due','canceled','expired')),
    CONSTRAINT ck_subscriptions_period CHECK (current_period_end IS NULL OR current_period_start IS NULL OR current_period_end > current_period_start)
)"""
    )

    op.execute(
        """CREATE UNIQUE INDEX uq_subscriptions_one_live_per_tenant ON subscriptions (tenant_id) WHERE status IN ('trialing','active','past_due')"""
    )

    op.execute(
        """CREATE INDEX ix_subscriptions_tenant_status ON subscriptions (tenant_id, status)"""
    )

    op.execute(
        """CREATE INDEX ix_subscriptions_plan_id ON subscriptions (plan_id)"""
    )

    op.execute(
        """CREATE UNIQUE INDEX uq_subscriptions_provider ON subscriptions (provider, provider_subscription_id) WHERE provider_subscription_id IS NOT NULL"""
    )

    op.execute(
        """CREATE INDEX ix_subscriptions_period_end ON subscriptions (current_period_end) WHERE status IN ('trialing','active','past_due')"""
    )

    op.execute(
        """CREATE TRIGGER trg_subscriptions_set_updated_at BEFORE UPDATE ON subscriptions
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS subscriptions")
