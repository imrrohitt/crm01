"""
Create automation_rules.

Revision: 20261028_200032
"""

from alembic import op

revision = "20261028_200032"
down_revision = '20261028_200031'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    social_account_id UUID,
    name TEXT NOT NULL,
    description TEXT,
    trigger_type TEXT NOT NULL,
    trigger_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    action_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft',
    priority INTEGER NOT NULL DEFAULT 100,
    created_by_membership_id UUID,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_automation_rules_tenant FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE CASCADE,
    CONSTRAINT fk_automation_rules_account FOREIGN KEY (tenant_id, social_account_id) REFERENCES social_accounts (tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_automation_rules_created_by FOREIGN KEY (tenant_id, created_by_membership_id) REFERENCES tenant_memberships (tenant_id, id) ON DELETE SET NULL (created_by_membership_id),
    CONSTRAINT uq_automation_rules_tenant_id_id UNIQUE (tenant_id, id),
    CONSTRAINT ck_automation_rules_status CHECK (status IN ('draft','active','paused','archived'))
)"""
    )

    op.execute(
        """CREATE INDEX ix_automation_rules_active ON automation_rules (tenant_id, trigger_type, priority) WHERE status = 'active'"""
    )

    op.execute(
        """CREATE INDEX ix_automation_rules_trigger_config ON automation_rules USING GIN (trigger_config jsonb_path_ops)"""
    )

    op.execute(
        """CREATE INDEX ix_automation_rules_additional_attributes ON automation_rules USING GIN (additional_attributes jsonb_path_ops)"""
    )

    op.execute(
        """CREATE TRIGGER trg_automation_rules_set_updated_at BEFORE UPDATE ON automation_rules
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS automation_rules")
