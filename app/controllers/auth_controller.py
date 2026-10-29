"""
Auth endpoints: login, refresh, me.
"""

import uuid

from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.controllers.base_controller import BaseController, before_action
from app.controllers.concerns.authenticatable import Authenticatable
from app.models import TenantMembership, User
from app.schemas.auth import LoginRequest, RefreshRequest
from app.services.auth_service import AuthError, AuthService, user_dict


class AuthController(Authenticatable, BaseController):
    @before_action(only=["me"])
    def require_login(self) -> None:
        self.authenticate_user()

    def login(self) -> JSONResponse:
        """POST /api/v1/auth/login  {email, password}"""
        try:
            data = LoginRequest(**self.params)
        except ValidationError:
            return self.render_error("A valid email and password are required", 422)
        try:
            return self.render_json(AuthService(self.db).login(data.email, data.password))
        except AuthError as e:
            return self.render_error(e.message, e.status)

    def refresh(self) -> JSONResponse:
        """POST /api/v1/auth/refresh  {refresh_token}"""
        try:
            data = RefreshRequest(**self.params)
        except ValidationError:
            return self.render_error("refresh_token is required", 422)
        try:
            return self.render_json(AuthService(self.db).refresh(data.refresh_token))
        except AuthError as e:
            return self.render_error(e.message, e.status)

    def me(self) -> JSONResponse:
        """GET /api/v1/auth/me  (Bearer access token)"""
        user = self.db.get(User, uuid.UUID(self._user_id()))
        if not user or not user.is_active:
            return self.render_error("Account not found or inactive", 401)
        service = AuthService(self.db)
        return self.render_json({"user": user_dict(user), "companies": service.companies_for(user)})
