"""
Create lead_assignments.

Several members may work one lead.

Revision: 20261028_200029
"""

from alembic import op

revision = "20261028_200029"
down_revision = '20261028_200028'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE lead_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    lead_id UUID NOT NULL,
    membership_id UUID NOT NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    unassigned_at TIMESTAMPTZ,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_lead_assignments_lead FOREIGN KEY (tenant_id, lead_id) REFERENCES leads (tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_lead_assignments_membership FOREIGN KEY (tenant_id, membership_id) REFERENCES tenant_memberships (tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT ck_lead_assignments_window CHECK (unassigned_at IS NULL OR unassigned_at >= assigned_at)
)"""
    )

    op.execute(
        """CREATE UNIQUE INDEX uq_lead_assignments_current ON lead_assignments (lead_id, membership_id) WHERE unassigned_at IS NULL"""
    )

    op.execute(
        """CREATE INDEX ix_lead_assignments_membership ON lead_assignments (tenant_id, membership_id) WHERE unassigned_at IS NULL"""
    )

    op.execute(
        """CREATE TRIGGER trg_lead_assignments_set_updated_at BEFORE UPDATE ON lead_assignments
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS lead_assignments")
