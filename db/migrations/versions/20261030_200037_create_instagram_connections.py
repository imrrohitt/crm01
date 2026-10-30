"""
Create instagram_connections.

Manual Instagram credentials for a company, plus the webhook URL and verify token
issued for that connection.

Revision: 20261030_200037
"""

from alembic import op

revision = "20261030_200037"
down_revision = "20261028_200036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE instagram_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    instagram_app_id TEXT NOT NULL,
    access_token_encrypted BYTEA NOT NULL,
    key_version INTEGER NOT NULL DEFAULT 1,
    webhook_verify_token TEXT NOT NULL,
    webhook_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'connected',
    connected_by_user_id UUID,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_instagram_connections_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_instagram_connections_connected_by FOREIGN KEY (connected_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT uq_instagram_connections_tenant_app UNIQUE (tenant_id, instagram_app_id),
    CONSTRAINT uq_instagram_connections_verify_token UNIQUE (webhook_verify_token),
    CONSTRAINT ck_instagram_connections_status CHECK (status IN ('connected','disconnected'))
)"""
    )

    op.execute(
        """CREATE INDEX ix_instagram_connections_tenant_status ON instagram_connections (tenant_id, status)"""
    )

    op.execute(
        """CREATE TRIGGER trg_instagram_connections_set_updated_at BEFORE UPDATE ON instagram_connections
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS instagram_connections")
