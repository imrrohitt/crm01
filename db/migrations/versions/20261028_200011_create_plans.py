"""
Create plans.

Revision: 20261028_200011
"""

from alembic import op

revision = "20261028_200011"
down_revision = '20261028_200010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    price NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    billing_interval TEXT NOT NULL DEFAULT 'monthly',
    is_active BOOLEAN NOT NULL DEFAULT true,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_plans_code UNIQUE (code),
    CONSTRAINT ck_plans_price CHECK (price >= 0),
    CONSTRAINT ck_plans_billing_interval CHECK (billing_interval IN ('monthly','yearly'))
)"""
    )

    op.execute(
        """CREATE TRIGGER trg_plans_set_updated_at BEFORE UPDATE ON plans
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS plans")
