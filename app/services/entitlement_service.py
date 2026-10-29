"""
Entitlements: which features a tenant gets from its subscription's plan.

While SUBSCRIPTION_ENFORCED is False (the default) every active tenant counts as
subscribed; the plan's features are still returned so the UI can show them.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Feature, PlanFeature, Subscription
from config.settings import get_settings


class EntitlementService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def current_subscription(self, tenant_id: uuid.UUID) -> Subscription | None:
        stmt = (
            select(Subscription)
            .where(Subscription.tenant_id == tenant_id, Subscription.status.in_(Subscription.LIVE_STATUSES))
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def has_access(self, tenant_id: uuid.UUID) -> bool:
        if not get_settings().SUBSCRIPTION_ENFORCED:
            return True
        return self.current_subscription(tenant_id) is not None

    def features(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        """{feature_code: value} from the tenant's plan; empty when it has no subscription."""
        sub = self.current_subscription(tenant_id)
        if sub is None:
            return {}
        stmt = (
            select(Feature.code, PlanFeature.value_json)
            .join(PlanFeature, PlanFeature.feature_id == Feature.id)
            .where(PlanFeature.plan_id == sub.plan_id, Feature.is_active.is_(True))
        )
        return {code: value for code, value in self.db.execute(stmt).all()}

    def summary(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        sub = self.current_subscription(tenant_id)
        return {
            "has_access": self.has_access(tenant_id),
            "plan": sub.plan.code if sub else None,
            "status": sub.status if sub else None,
            "features": self.features(tenant_id),
        }
