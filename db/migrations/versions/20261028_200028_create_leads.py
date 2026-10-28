"""
Create leads.

Revision: 20261028_200028
"""

from alembic import op

revision = "20261028_200028"
down_revision = '20261028_200027'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    contact_id UUID NOT NULL,
    title TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'new',
    value_amount NUMERIC(14,2),
    currency CHAR(3),
    source_conversation_id UUID,
    created_by_membership_id UUID,
    closed_at TIMESTAMPTZ,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_leads_contact FOREIGN KEY (tenant_id, contact_id) REFERENCES contacts (tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_leads_source_conversation FOREIGN KEY (tenant_id, source_conversation_id) REFERENCES conversations (tenant_id, id) ON DELETE SET NULL (source_conversation_id),
    CONSTRAINT fk_leads_created_by FOREIGN KEY (tenant_id, created_by_membership_id) REFERENCES tenant_memberships (tenant_id, id) ON DELETE SET NULL (created_by_membership_id),
    CONSTRAINT uq_leads_tenant_id_id UNIQUE (tenant_id, id),
    CONSTRAINT ck_leads_stage CHECK (stage IN ('new','qualified','proposal','won','lost')),
    CONSTRAINT ck_leads_value CHECK (value_amount IS NULL OR value_amount >= 0),
    CONSTRAINT ck_leads_value_has_currency CHECK (value_amount IS NULL OR currency IS NOT NULL)
)"""
    )

    op.execute(
        """CREATE INDEX ix_leads_pipeline ON leads (tenant_id, stage, created_at DESC)"""
    )

    op.execute(
        """CREATE INDEX ix_leads_contact ON leads (contact_id)"""
    )

    op.execute(
        """CREATE INDEX ix_leads_title_trgm ON leads USING GIN (title gin_trgm_ops)"""
    )

    op.execute(
        """CREATE INDEX ix_leads_additional_attributes ON leads USING GIN (additional_attributes jsonb_path_ops)"""
    )

    op.execute(
        """CREATE TRIGGER trg_leads_set_updated_at BEFORE UPDATE ON leads
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS leads")
