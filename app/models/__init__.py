"""
Models package — single source for app-wide model access.
Import all application models here; then use "from app.models import ModelName" everywhere.
Only SQLAlchemy models perform CRUD; schemas are for validation/serialization only.
"""

from app.models.base_model import BaseModel
from app.models.concerns.timestampable import Timestampable
from app.models.concerns.soft_deletable import SoftDeletable
from app.models.concerns.sluggable import Sluggable
from app.models.user import User, UserProfile
from app.models.tenant import Tenant
from app.models.tenant_membership import (
    MembershipRole,
    Permission,
    Role,
    RolePermission,
    TenantMembership,
)
from app.models.social_account import SocialAccount, SocialAccountToken
from app.models.instagram_connection import InstagramConnection
from app.models.webhook_event import WebhookEvent
from app.models.plan import Feature, Plan, PlanFeature, Subscription

__all__ = [
    "BaseModel",
    "Timestampable",
    "SoftDeletable",
    "Sluggable",
    "User",
    "UserProfile",
    "Tenant",
    "TenantMembership",
    "Role",
    "Permission",
    "RolePermission",
    "MembershipRole",
    "Plan",
    "Feature",
    "PlanFeature",
    "Subscription",
    "SocialAccount",
    "SocialAccountToken",
    "InstagramConnection",
    "WebhookEvent",
]
