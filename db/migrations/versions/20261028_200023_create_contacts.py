"""
Create contacts.

People who DM the connected Instagram account. Account-scoped; NOT CRM users.

Revision: 20261028_200023
"""

from alembic import op

revision = "20261028_200023"
down_revision = '20261028_200022'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    social_account_id UUID NOT NULL,
    platform_user_id TEXT NOT NULL,
    username TEXT,
    display_name TEXT,
    profile_picture_url TEXT,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_interaction_at TIMESTAMPTZ,
    source TEXT NOT NULL DEFAULT 'instagram_dm',
    custom_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_contacts_account FOREIGN KEY (tenant_id, social_account_id) REFERENCES social_accounts (tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT uq_contacts_account_platform_user UNIQUE (social_account_id, platform_user_id),
    CONSTRAINT uq_contacts_tenant_id_id UNIQUE (tenant_id, id),
    CONSTRAINT uq_contacts_tenant_account_id UNIQUE (tenant_id, social_account_id, id)
)"""
    )

    op.execute(
        """CREATE INDEX ix_contacts_tenant_last_interaction ON contacts (tenant_id, last_interaction_at DESC NULLS LAST)"""
    )

    op.execute(
        """CREATE INDEX ix_contacts_username_trgm ON contacts USING GIN (username gin_trgm_ops)"""
    )

    op.execute(
        """CREATE INDEX ix_contacts_display_name_trgm ON contacts USING GIN (display_name gin_trgm_ops)"""
    )

    op.execute(
        """CREATE INDEX ix_contacts_custom_fields ON contacts USING GIN (custom_fields jsonb_path_ops)"""
    )

    op.execute(
        """CREATE INDEX ix_contacts_additional_attributes ON contacts USING GIN (additional_attributes jsonb_path_ops)"""
    )

    op.execute(
        """CREATE TRIGGER trg_contacts_set_updated_at BEFORE UPDATE ON contacts
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS contacts")
