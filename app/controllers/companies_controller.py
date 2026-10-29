"""
Companies (tenants) the logged-in user belongs to.
"""

import uuid

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.controllers.base_controller import BaseController, before_action
from app.controllers.concerns.authenticatable import Authenticatable
from app.models import User
from app.services.auth_service import AuthService, user_dict
from app.services.entitlement_service import EntitlementService


class CompaniesController(Authenticatable, BaseController):
    @before_action
    def require_login(self) -> None:
        self.authenticate_user()

    def index(self) -> JSONResponse:
        """GET /api/v1/companies"""
        user = self._load_user()
        return self.render_json(AuthService(self.db).companies_for(user))

    def show(self) -> JSONResponse:
        """GET /api/v1/companies/{id}: company, my roles, subscription and features."""
        user = self._load_user()
        company_id: uuid.UUID = self.params["id"]
        # Non-members get 404 (not 403) so company ids cannot be probed.
        company = next((c for c in AuthService(self.db).companies_for(user) if c["id"] == company_id), None)
        if company is None:
            raise HTTPException(status_code=404, detail="Company not found")
        return self.render_json(
            {
                **company,
                "user": user_dict(user),
                "subscription": EntitlementService(self.db).summary(company_id),
            }
        )

    def _load_user(self) -> User:
        user = self.db.get(User, uuid.UUID(self._user_id()))
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Account not found or inactive")
        return user
