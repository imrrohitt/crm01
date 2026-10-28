"""
Create user_profiles.

Personal profile, strictly 1:1 with users (no tenant_id on purpose).

Revision: 20261028_200002
"""

from alembic import op

revision = "20261028_200002"
down_revision = '20261028_200001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY,
    full_name TEXT NOT NULL,
    avatar_url TEXT,
    phone TEXT,
    locale TEXT NOT NULL DEFAULT 'en',
    timezone TEXT,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_user_profiles_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
)"""
    )

    op.execute(
        """CREATE INDEX ix_user_profiles_full_name_trgm ON user_profiles USING GIN (full_name gin_trgm_ops)"""
    )

    op.execute(
        """CREATE TRIGGER trg_user_profiles_set_updated_at BEFORE UPDATE ON user_profiles
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_profiles")
