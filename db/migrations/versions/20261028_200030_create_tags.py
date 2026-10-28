"""
Create tags.

Revision: 20261028_200030
"""

from alembic import op

revision = "20261028_200030"
down_revision = '20261028_200029'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name TEXT NOT NULL,
    color TEXT,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_tags_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT uq_tags_tenant_id_id UNIQUE (tenant_id, id)
)"""
    )

    op.execute(
        """CREATE UNIQUE INDEX uq_tags_tenant_name ON tags (tenant_id, lower(name))"""
    )

    op.execute(
        """CREATE TRIGGER trg_tags_set_updated_at BEFORE UPDATE ON tags
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tags")
