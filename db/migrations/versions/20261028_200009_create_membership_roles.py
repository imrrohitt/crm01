"""
Create membership_roles.

A membership may hold several roles. System roles (tenant_id NULL) are valid everywhere; tenant roles only in their own tenant.

Revision: 20261028_200009
"""

from alembic import op

revision = "20261028_200009"
down_revision = '20261028_200008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE membership_roles (
    membership_id UUID NOT NULL,
    role_id UUID NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    additional_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_membership_roles PRIMARY KEY (membership_id, role_id),
    CONSTRAINT fk_membership_roles_membership FOREIGN KEY (membership_id) REFERENCES tenant_memberships (id) ON DELETE CASCADE,
    CONSTRAINT fk_membership_roles_role FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE
)"""
    )

    op.execute(
        """CREATE INDEX ix_membership_roles_role_id ON membership_roles (role_id)"""
    )

    op.execute(
        """CREATE TRIGGER trg_membership_roles_set_updated_at BEFORE UPDATE ON membership_roles
FOR EACH ROW EXECUTE FUNCTION set_updated_at()"""
    )

    op.execute(
        """CREATE FUNCTION check_membership_role_tenant() RETURNS trigger AS $$
DECLARE m_tenant UUID; r_tenant UUID;
BEGIN
    SELECT tenant_id INTO m_tenant FROM tenant_memberships WHERE id = NEW.membership_id;
    SELECT tenant_id INTO r_tenant FROM roles WHERE id = NEW.role_id;
    IF r_tenant IS NOT NULL AND r_tenant <> m_tenant THEN
        RAISE EXCEPTION 'role % belongs to a different tenant than membership %', NEW.role_id, NEW.membership_id;
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql"""
    )

    op.execute(
        """CREATE TRIGGER trg_membership_roles_check_tenant BEFORE INSERT OR UPDATE ON membership_roles
FOR EACH ROW EXECUTE FUNCTION check_membership_role_tenant()"""
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS check_membership_role_tenant() CASCADE")
    op.execute("DROP TABLE IF EXISTS membership_roles")
