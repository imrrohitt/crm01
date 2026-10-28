"""
Create audit_logs.

Append-only. BRIN on created_at stays tiny on a huge insert-ordered table.

Revision: 20261028_200036
"""

from alembic import op

revision = "20261028_200036"
down_revision = '20261028_200035'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    actor_membership_id UUID,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id UUID,
    ip_address INET,
    user_agent TEXT,
    changes JSONB NOT NULL DEFAULT '{}'::jsonb,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_audit_logs_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_audit_logs_actor FOREIGN KEY (tenant_id, actor_membership_id) REFERENCES tenant_memberships (tenant_id, id) ON DELETE SET NULL (actor_membership_id)
)"""
    )

    op.execute(
        """CREATE INDEX ix_audit_logs_tenant_created ON audit_logs (tenant_id, created_at DESC)"""
    )

    op.execute(
        """CREATE INDEX ix_audit_logs_resource ON audit_logs (tenant_id, resource_type, resource_id)"""
    )

    op.execute(
        """CREATE INDEX ix_audit_logs_created_brin ON audit_logs USING BRIN (created_at)"""
    )

    op.execute(
        """CREATE INDEX ix_audit_logs_changes ON audit_logs USING GIN (changes jsonb_path_ops)"""
    )

    op.execute(
        """CREATE TRIGGER trg_audit_logs_set_updated_at BEFORE UPDATE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_logs")
