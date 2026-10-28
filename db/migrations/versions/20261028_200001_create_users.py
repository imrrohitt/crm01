"""
Create users.

Global login identity. No tenant_id: one user can belong to many tenants via tenant_memberships.

Revision: 20261028_200001
"""

from alembic import op

revision = "20261028_200001"
down_revision = '20261028_200000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    password_hash TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    email_verified_at TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT ck_users_email_lowercase CHECK (email = lower(btrim(email))),
    CONSTRAINT ck_users_status CHECK (status IN ('active','blocked','pending'))
)"""
    )

    op.execute(
        """CREATE TRIGGER trg_users_set_updated_at BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS users")
