"""
Create tenant_member_profiles.

Optional per-company profile override (name/avatar/title differ per tenant).

Revision: 20261028_200008
"""

from alembic import op

revision = "20261028_200008"
down_revision = '20261028_200007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE tenant_member_profiles (
    membership_id UUID PRIMARY KEY,
    display_name TEXT NOT NULL,
    avatar_url TEXT,
    job_title TEXT,
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_tenant_member_profiles_membership FOREIGN KEY (membership_id) REFERENCES tenant_memberships (id) ON DELETE CASCADE
)"""
    )

    op.execute(
        """CREATE TRIGGER trg_tenant_member_profiles_set_updated_at BEFORE UPDATE ON tenant_member_profiles
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_member_profiles")
