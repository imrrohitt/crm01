"""
Create tenant_settings.

Revision: 20261028_200018
"""

from alembic import op

revision = "20261028_200018"
down_revision = '20261028_200017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE tenant_settings (
    tenant_id UUID PRIMARY KEY,
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_tenant_settings_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)"""
    )

    op.execute(
        """CREATE INDEX ix_tenant_settings_settings ON tenant_settings USING GIN (settings jsonb_path_ops)"""
    )

    op.execute(
        """CREATE TRIGGER trg_tenant_settings_set_updated_at BEFORE UPDATE ON tenant_settings
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_settings")
