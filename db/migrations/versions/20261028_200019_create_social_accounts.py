"""
Create social_accounts.

Globally unique per (platform, platform_account_id): one Instagram account belongs to one tenant.

Revision: 20261028_200019
"""

from alembic import op

revision = "20261028_200019"
down_revision = '20261028_200018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    platform TEXT NOT NULL DEFAULT 'instagram',
    platform_account_id TEXT NOT NULL,
    username TEXT,
    account_type TEXT,
    status TEXT NOT NULL DEFAULT 'connected',
    connected_by_user_id UUID,
    connected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    disconnected_at TIMESTAMPTZ,
    last_synced_at TIMESTAMPTZ,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_social_accounts_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_social_accounts_connected_by FOREIGN KEY (connected_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT uq_social_accounts_platform_account UNIQUE (platform, platform_account_id),
    CONSTRAINT uq_social_accounts_tenant_id_id UNIQUE (tenant_id, id),
    CONSTRAINT ck_social_accounts_platform CHECK (platform IN ('instagram')),
    CONSTRAINT ck_social_accounts_status CHECK (status IN ('connected','disconnected','error'))
)"""
    )

    op.execute(
        """CREATE INDEX ix_social_accounts_tenant_status ON social_accounts (tenant_id, status)"""
    )

    op.execute(
        """CREATE INDEX ix_social_accounts_username_trgm ON social_accounts USING GIN (username gin_trgm_ops)"""
    )

    op.execute(
        """CREATE INDEX ix_social_accounts_additional_attributes ON social_accounts USING GIN (additional_attributes jsonb_path_ops)"""
    )

    op.execute(
        """CREATE TRIGGER trg_social_accounts_set_updated_at BEFORE UPDATE ON social_accounts
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS social_accounts")
