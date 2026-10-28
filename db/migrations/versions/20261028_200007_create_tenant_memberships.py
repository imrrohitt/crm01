"""
Create tenant_memberships.

User <-> tenant link. All 'who works in which company' queries go through here.

Revision: 20261028_200007
"""

from alembic import op

revision = "20261028_200007"
down_revision = '20261028_200006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE tenant_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    status TEXT NOT NULL DEFAULT 'invited',
    job_title TEXT,
    joined_at TIMESTAMPTZ,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_tenant_memberships_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_tenant_memberships_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT uq_tenant_memberships_tenant_user UNIQUE (tenant_id, user_id),
    CONSTRAINT uq_tenant_memberships_tenant_id_id UNIQUE (tenant_id, id),
    CONSTRAINT ck_tenant_memberships_status CHECK (status IN ('invited','active','suspended','removed'))
)"""
    )

    op.execute(
        """CREATE INDEX ix_tenant_memberships_user_status ON tenant_memberships (user_id, status)"""
    )

    op.execute(
        """CREATE INDEX ix_tenant_memberships_tenant_status ON tenant_memberships (tenant_id, status)"""
    )

    op.execute(
        """CREATE TRIGGER trg_tenant_memberships_set_updated_at BEFORE UPDATE ON tenant_memberships
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_memberships")
