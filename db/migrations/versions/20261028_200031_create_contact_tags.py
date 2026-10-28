"""
Create contact_tags.

Composite FKs make it impossible to attach another tenant's tag to a contact.

Revision: 20261028_200031
"""

from alembic import op

revision = "20261028_200031"
down_revision = '20261028_200030'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE contact_tags (
    tenant_id UUID NOT NULL,
    contact_id UUID NOT NULL,
    tag_id UUID NOT NULL,
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_contact_tags PRIMARY KEY (contact_id, tag_id),
    CONSTRAINT fk_contact_tags_contact FOREIGN KEY (tenant_id, contact_id) REFERENCES contacts (tenant_id, id) ON DELETE CASCADE,
    CONSTRAINT fk_contact_tags_tag FOREIGN KEY (tenant_id, tag_id) REFERENCES tags (tenant_id, id) ON DELETE CASCADE
)"""
    )

    op.execute(
        """CREATE INDEX ix_contact_tags_tag ON contact_tags (tenant_id, tag_id)"""
    )

    op.execute(
        """CREATE TRIGGER trg_contact_tags_set_updated_at BEFORE UPDATE ON contact_tags
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS contact_tags")
