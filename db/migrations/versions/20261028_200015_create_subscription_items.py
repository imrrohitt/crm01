"""
Create subscription_items.

Add-ons on top of the base plan (extra seats, extra Instagram accounts, paid modules).

Revision: 20261028_200015
"""

from alembic import op

revision = "20261028_200015"
down_revision = '20261028_200014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE subscription_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL,
    item_type TEXT NOT NULL,
    reference_id UUID,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(12,2) NOT NULL DEFAULT 0,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_subscription_items_subscription FOREIGN KEY (subscription_id) REFERENCES subscriptions (id) ON DELETE CASCADE,
    CONSTRAINT ck_subscription_items_quantity CHECK (quantity > 0),
    CONSTRAINT ck_subscription_items_unit_price CHECK (unit_price >= 0),
    CONSTRAINT ck_subscription_items_type CHECK (item_type IN ('addon','extra_seat','extra_social_account','module'))
)"""
    )

    op.execute(
        """CREATE INDEX ix_subscription_items_subscription_id ON subscription_items (subscription_id)"""
    )

    op.execute(
        """CREATE TRIGGER trg_subscription_items_set_updated_at BEFORE UPDATE ON subscription_items
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS subscription_items")
