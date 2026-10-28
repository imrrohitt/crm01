"""
Create tenant_feature_overrides.

Per-tenant exceptions layered over plan_features (e.g. 30 days of AI replies as a gift).

Revision: 20261028_200017
"""

from alembic import op

revision = "20261028_200017"
down_revision = '20261028_200016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE tenant_feature_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    feature_id UUID NOT NULL,
    value_json JSONB NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    reason TEXT,
    created_by_user_id UUID,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_tenant_feature_overrides_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_tenant_feature_overrides_feature FOREIGN KEY (feature_id) REFERENCES features (id) ON DELETE CASCADE,
    CONSTRAINT fk_tenant_feature_overrides_created_by FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT ck_tenant_feature_overrides_window CHECK (expires_at IS NULL OR expires_at > starts_at)
)"""
    )

    op.execute(
        """CREATE INDEX ix_tenant_feature_overrides_lookup ON tenant_feature_overrides (tenant_id, feature_id, starts_at DESC)"""
    )

    op.execute(
        """CREATE TRIGGER trg_tenant_feature_overrides_set_updated_at BEFORE UPDATE ON tenant_feature_overrides
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_feature_overrides")
