"""
Create usage_counters.

Increment atomically: INSERT ... ON CONFLICT (tenant_id, feature_id, period_start) DO UPDATE SET used_value = usage_counters.used_value + EXCLUDED.used_value.

Revision: 20261028_200035
"""

from alembic import op

revision = "20261028_200035"
down_revision = '20261028_200034'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE usage_counters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    feature_id UUID NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    used_value BIGINT NOT NULL DEFAULT 0,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_usage_counters_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_usage_counters_feature FOREIGN KEY (feature_id) REFERENCES features (id) ON DELETE CASCADE,
    CONSTRAINT uq_usage_counters_period UNIQUE (tenant_id, feature_id, period_start),
    CONSTRAINT ck_usage_counters_period CHECK (period_end > period_start),
    CONSTRAINT ck_usage_counters_used CHECK (used_value >= 0)
)"""
    )

    op.execute(
        """CREATE TRIGGER trg_usage_counters_set_updated_at BEFORE UPDATE ON usage_counters
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS usage_counters")
