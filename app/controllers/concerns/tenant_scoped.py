"""
TenantScoped concern: resolve the company from the URL and check the caller's membership.
Non-members get 404 (not 403) so company ids cannot be probed.
"""

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Role, Tenant, TenantMembership


class TenantScoped:
    membership: TenantMembership

    def load_membership(self) -> TenantMembership:
        """Sets self.membership for params["company_id"] and the logged-in user."""
        company_id: uuid.UUID = self.params["company_id"]
        stmt = (
            select(TenantMembership)
            .join(Tenant, Tenant.id == TenantMembership.tenant_id)
            .options(selectinload(TenantMembership.roles).selectinload(Role.permissions))
            .where(
                TenantMembership.tenant_id == company_id,
                TenantMembership.user_id == uuid.UUID(self._user_id()),
                TenantMembership.status == "active",
                Tenant.status == "active",
            )
        )
        membership = self.db.execute(stmt).scalars().first()
        if membership is None:
            raise HTTPException(status_code=404, detail="Company not found")
        self.membership = membership
        return membership

    def permission_codes(self) -> set[str]:
        return {p.code for r in self.membership.roles for p in r.permissions}

    def require_permission(self, code: str) -> None:
        if code not in self.permission_codes():
            raise HTTPException(status_code=403, detail="You do not have permission to do this")
