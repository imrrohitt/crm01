"""
Postgres extensions and the shared set_updated_at() trigger function.

Every table gets: additional_attributes JSONB (free-form extra data),
created_at and updated_at (maintained by trigger).

Revision: 20261028_200000
"""

from alembic import op

revision = "20261028_200000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """CREATE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END $$ LANGUAGE plpgsql"""
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
