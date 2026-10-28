"""
Create plan_features.

value_json: true/false for boolean features, a number for limits, an object for config.

Revision: 20261028_200013
"""

from alembic import op

revision = "20261028_200013"
down_revision = '20261028_200012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE plan_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL,
    feature_id UUID NOT NULL,
    value_json JSONB NOT NULL,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_plan_features_plan FOREIGN KEY (plan_id) REFERENCES plans (id) ON DELETE CASCADE,
    CONSTRAINT fk_plan_features_feature FOREIGN KEY (feature_id) REFERENCES features (id) ON DELETE CASCADE,
    CONSTRAINT uq_plan_features_plan_feature UNIQUE (plan_id, feature_id)
)"""
    )

    op.execute(
        """CREATE INDEX ix_plan_features_feature_id ON plan_features (feature_id)"""
    )

    op.execute(
        """CREATE TRIGGER trg_plan_features_set_updated_at BEFORE UPDATE ON plan_features
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS plan_features")
