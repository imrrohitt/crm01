"""
Create tenants.

One influencer / business = one tenant.

Revision: 20261028_200003
"""

from alembic import op

revision = "20261028_200003"
down_revision = '20261028_200002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    owner_user_id UUID NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    suspended_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tenants_slug UNIQUE (slug),
    CONSTRAINT ck_tenants_slug_format CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
    CONSTRAINT ck_tenants_status CHECK (status IN ('active','suspended','deleted')),
    CONSTRAINT fk_tenants_owner FOREIGN KEY (owner_user_id) REFERENCES users (id) ON DELETE RESTRICT
)"""
    )

    op.execute(
        """CREATE INDEX ix_tenants_owner_user_id ON tenants (owner_user_id)"""
    )

    op.execute(
        """CREATE INDEX ix_tenants_status ON tenants (status) WHERE status <> 'active'"""
    )

    op.execute(
        """CREATE INDEX ix_tenants_name_trgm ON tenants USING GIN (name gin_trgm_ops)"""
    )

    op.execute(
        """CREATE TRIGGER trg_tenants_set_updated_at BEFORE UPDATE ON tenants
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenants")
