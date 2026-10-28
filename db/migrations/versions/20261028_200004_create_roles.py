"""
Create roles.

tenant_id NULL = system role (owner, admin, manager, agent, viewer); otherwise a custom tenant role.

Revision: 20261028_200004
"""

from alembic import op

revision = "20261028_200004"
down_revision = '20261028_200003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_system BOOLEAN NOT NULL DEFAULT false,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_roles_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT ck_roles_system_has_no_tenant CHECK (NOT is_system OR tenant_id IS NULL)
)"""
    )

    op.execute(
        """CREATE UNIQUE INDEX uq_roles_tenant_code ON roles (tenant_id, code) WHERE tenant_id IS NOT NULL"""
    )

    op.execute(
        """CREATE UNIQUE INDEX uq_roles_system_code ON roles (code) WHERE tenant_id IS NULL"""
    )

    op.execute(
        """CREATE TRIGGER trg_roles_set_updated_at BEFORE UPDATE ON roles
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS roles")
