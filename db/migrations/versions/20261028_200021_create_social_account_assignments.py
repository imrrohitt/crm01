"""
Create social_account_assignments.

Restricts a team member to specific Instagram accounts.

Revision: 20261028_200021
"""

from alembic import op

revision = "20261028_200021"
down_revision = '20261028_200020'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE social_account_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    social_account_id UUID NOT NULL,
    membership_id UUID NOT NULL,
    assigned_by_membership_id UUID,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_social_account_assignments_account FOREIGN KEY (tenant_id, social_account_id) REFERENCES social_accounts (tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_social_account_assignments_membership FOREIGN KEY (tenant_id, membership_id) REFERENCES tenant_memberships (tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_social_account_assignments_assigned_by FOREIGN KEY (tenant_id, assigned_by_membership_id) REFERENCES tenant_memberships (tenant_id, id) ON DELETE SET NULL (assigned_by_membership_id),
    CONSTRAINT uq_social_account_assignments_pair UNIQUE (social_account_id, membership_id)
)"""
    )

    op.execute(
        """CREATE INDEX ix_social_account_assignments_membership ON social_account_assignments (membership_id)"""
    )

    op.execute(
        """CREATE TRIGGER trg_social_account_assignments_set_updated_at BEFORE UPDATE ON social_account_assignments
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS social_account_assignments")
