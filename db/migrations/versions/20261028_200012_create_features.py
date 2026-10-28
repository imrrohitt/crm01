"""
Create features.

Catalog of everything that can be sold or limited (instagram_accounts, team_members, ai_replies...).

Revision: 20261028_200012
"""

from alembic import op

revision = "20261028_200012"
down_revision = '20261028_200011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    value_type TEXT NOT NULL DEFAULT 'boolean',
    unit TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_features_code UNIQUE (code),
    CONSTRAINT ck_features_value_type CHECK (value_type IN ('boolean','integer','string','json'))
)"""
    )

    op.execute(
        """CREATE TRIGGER trg_features_set_updated_at BEFORE UPDATE ON features
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS features")
