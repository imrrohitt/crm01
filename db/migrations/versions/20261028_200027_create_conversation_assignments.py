"""
Create conversation_assignments.

History kept: reassigning closes the old row (unassigned_at) and inserts a new one. Only one open row per conversation.

Revision: 20261028_200027
"""

from alembic import op

revision = "20261028_200027"
down_revision = '20261028_200026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE conversation_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    conversation_id UUID NOT NULL,
    membership_id UUID NOT NULL,
    assigned_by_membership_id UUID,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    unassigned_at TIMESTAMPTZ,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_conversation_assignments_conversation FOREIGN KEY (tenant_id, conversation_id) REFERENCES conversations (tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_conversation_assignments_membership FOREIGN KEY (tenant_id, membership_id) REFERENCES tenant_memberships (tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_conversation_assignments_assigned_by FOREIGN KEY (tenant_id, assigned_by_membership_id) REFERENCES tenant_memberships (tenant_id, id) ON DELETE SET NULL (assigned_by_membership_id),
    CONSTRAINT ck_conversation_assignments_window CHECK (unassigned_at IS NULL OR unassigned_at >= assigned_at)
)"""
    )

    op.execute(
        """CREATE UNIQUE INDEX uq_conversation_assignments_current ON conversation_assignments (conversation_id) WHERE unassigned_at IS NULL"""
    )

    op.execute(
        """CREATE INDEX ix_conversation_assignments_agent_inbox ON conversation_assignments (tenant_id, membership_id) WHERE unassigned_at IS NULL"""
    )

    op.execute(
        """CREATE TRIGGER trg_conversation_assignments_set_updated_at BEFORE UPDATE ON conversation_assignments
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS conversation_assignments")
