"""
Create permissions.

Permission catalog, e.g. contacts.read, conversations.reply, billing.manage.

Revision: 20261028_200005
"""

from alembic import op

revision = "20261028_200005"
down_revision = '20261028_200004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL,
    description TEXT,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_permissions_code UNIQUE (code)
)"""
    )

    op.execute(
        """CREATE TRIGGER trg_permissions_set_updated_at BEFORE UPDATE ON permissions
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS permissions")
