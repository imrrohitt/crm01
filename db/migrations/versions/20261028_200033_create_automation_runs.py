"""
Create automation_runs.

Revision: 20261028_200033
"""

from alembic import op

revision = "20261028_200033"
down_revision = '20261028_200032'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE automation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    automation_rule_id UUID NOT NULL,
    conversation_id UUID,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    error TEXT,
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_automation_runs_rule FOREIGN KEY (tenant_id, automation_rule_id) REFERENCES automation_rules (tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_automation_runs_conversation FOREIGN KEY (tenant_id, conversation_id) REFERENCES conversations (tenant_id, id) ON DELETE SET NULL (conversation_id),
    CONSTRAINT ck_automation_runs_status CHECK (status IN ('running','succeeded','failed','skipped'))
)"""
    )

    op.execute(
        """CREATE INDEX ix_automation_runs_rule_started ON automation_runs (automation_rule_id, started_at DESC)"""
    )

    op.execute(
        """CREATE INDEX ix_automation_runs_tenant_started ON automation_runs (tenant_id, started_at DESC)"""
    )

    op.execute(
        """CREATE TRIGGER trg_automation_runs_set_updated_at BEFORE UPDATE ON automation_runs
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS automation_runs")
