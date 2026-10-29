"""
Database seeding. Idempotent: safe to run many times (python manage.py db seed).

Creates the system roles/permissions, a plan catalog with features, demo companies
with active subscriptions, and demo users who can log in.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import Session

from config.database import SessionLocal
from app.models import (
    Feature,
    MembershipRole,
    Permission,
    Plan,
    PlanFeature,
    Role,
    RolePermission,
    Subscription,
    Tenant,
    TenantMembership,
    User,
    UserProfile,
)

# Password for every demo user. Override with SEED_PASSWORD. Development only.
SEED_PASSWORD = os.environ.get("SEED_PASSWORD", "Password@123")

PERMISSIONS = {
    "contacts.read": "View contacts",
    "contacts.write": "Create and edit contacts",
    "conversations.read": "View conversations",
    "conversations.reply": "Reply to conversations",
    "leads.manage": "Manage leads",
    "team.manage": "Invite and manage team members",
    "billing.manage": "Manage subscription and billing",
    "settings.manage": "Change company settings",
}

ROLES = {
    "owner": ("Owner", list(PERMISSIONS)),
    "admin": ("Admin", [p for p in PERMISSIONS if p != "billing.manage"]),
    "manager": ("Manager", ["contacts.read", "contacts.write", "conversations.read", "conversations.reply", "leads.manage"]),
    "agent": ("Agent", ["contacts.read", "conversations.read", "conversations.reply"]),
    "viewer": ("Viewer", ["contacts.read", "conversations.read"]),
}

FEATURES = {
    "instagram_accounts": ("Instagram accounts", "integer", "accounts"),
    "team_members": ("Team members", "integer", "members"),
    "inbox": ("Unified inbox", "boolean", None),
    "contacts": ("Contacts", "boolean", None),
    "leads": ("Lead pipeline", "boolean", None),
    "campaigns": ("Campaigns", "boolean", None),
    "automation": ("Automation", "boolean", None),
    "ai_replies": ("AI replies", "boolean", None),
    "analytics": ("Advanced analytics", "boolean", None),
}

PLANS = {
    "starter": ("Starter", 999, {
        "instagram_accounts": 1, "team_members": 3, "inbox": True, "contacts": True,
        "leads": True, "campaigns": False, "automation": False, "ai_replies": False, "analytics": False,
    }),
    "pro": ("Pro", 2999, {
        "instagram_accounts": 5, "team_members": 10, "inbox": True, "contacts": True,
        "leads": True, "campaigns": True, "automation": True, "ai_replies": True, "analytics": True,
    }),
}

USERS = [
    # key, email, full name
    ("rahul", "rahul@rahulfitness.demo", "Rahul Verma"),
    ("priya", "priya@rahulfitness.demo", "Priya Singh"),
    ("aman", "aman@techwithaman.demo", "Aman Gupta"),
    ("rohit", "rohit@agency.demo", "Rohit Kushwaha"),
]

TENANTS = [
    # key, name, slug, owner, plan, [(user, role, job title)]
    ("rahul_fitness", "Rahul Fitness", "rahul-fitness", "rahul", "pro", [
        ("rahul", "owner", "Founder"),
        ("priya", "agent", "Support Agent"),
        ("rohit", "admin", "Social Media Manager"),
    ]),
    ("tech_with_aman", "Tech With Aman", "tech-with-aman", "aman", "pro", [
        ("aman", "owner", "Founder"),
        ("rohit", "agent", "Community Manager"),
    ]),
]


def _get_or_create(db: Session, model, where: dict, **defaults):
    obj = db.execute(select(model).filter_by(**where)).scalars().first()
    if obj:
        return obj, False
    obj = model(**where, **defaults)
    db.add(obj)
    db.flush()
    return obj, True


def seed_access_control(db: Session) -> dict[str, Role]:
    perms = {code: _get_or_create(db, Permission, {"code": code}, description=desc)[0] for code, desc in PERMISSIONS.items()}
    roles: dict[str, Role] = {}
    for code, (name, perm_codes) in ROLES.items():
        role = db.execute(select(Role).where(Role.code == code, Role.tenant_id.is_(None))).scalars().first()
        if not role:
            role = Role(code=code, name=name, is_system=True, tenant_id=None)
            db.add(role)
            db.flush()
        for pc in perm_codes:
            _get_or_create(db, RolePermission, {"role_id": role.id, "permission_id": perms[pc].id})
        roles[code] = role
    return roles


def seed_plans(db: Session) -> dict[str, Plan]:
    features = {
        code: _get_or_create(db, Feature, {"code": code}, name=name, value_type=vtype, unit=unit)[0]
        for code, (name, vtype, unit) in FEATURES.items()
    }
    plans: dict[str, Plan] = {}
    for code, (name, price, values) in PLANS.items():
        plan, _ = _get_or_create(db, Plan, {"code": code}, name=name, price=price, currency="INR", billing_interval="monthly")
        for fcode, value in values.items():
            pf, created = _get_or_create(db, PlanFeature, {"plan_id": plan.id, "feature_id": features[fcode].id}, value_json=value)
            if not created:
                pf.value_json = value
        plans[code] = plan
    return plans


def seed_users(db: Session) -> dict[str, User]:
    users: dict[str, User] = {}
    for key, email, full_name in USERS:
        user, created = _get_or_create(db, User, {"email": email}, status="active", email_verified_at=datetime.now(timezone.utc))
        if created or not user.password_hash:
            user.set_password(SEED_PASSWORD)
        _get_or_create(db, UserProfile, {"user_id": user.id}, full_name=full_name)
        users[key] = user
    return users


def seed_tenants(db: Session, users: dict[str, User], roles: dict[str, Role], plans: dict[str, Plan]) -> None:
    now = datetime.now(timezone.utc)
    for _key, name, slug, owner, plan_code, members in TENANTS:
        tenant, _ = _get_or_create(db, Tenant, {"slug": slug}, name=name, owner_user_id=users[owner].id, status="active", timezone="Asia/Kolkata")
        for user_key, role_code, title in members:
            membership, _ = _get_or_create(
                db, TenantMembership, {"tenant_id": tenant.id, "user_id": users[user_key].id},
                status="active", job_title=title, joined_at=now,
            )
            _get_or_create(db, MembershipRole, {"membership_id": membership.id, "role_id": roles[role_code].id})
        live = db.execute(
            select(Subscription).where(Subscription.tenant_id == tenant.id, Subscription.status.in_(Subscription.LIVE_STATUSES))
        ).scalars().first()
        if not live:
            db.add(Subscription(
                tenant_id=tenant.id, plan_id=plans[plan_code].id, status="active",
                starts_at=now, current_period_start=now, current_period_end=now + timedelta(days=365),
            ))


def run_seeds() -> None:
    db = SessionLocal()
    try:
        roles = seed_access_control(db)
        plans = seed_plans(db)
        users = seed_users(db)
        seed_tenants(db, users, roles, plans)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print(f"Seeded {len(USERS)} users, {len(TENANTS)} companies, {len(PLANS)} plans.")
    print("Demo logins (password in db/seeds.py, SEED_PASSWORD):")
    for _key, email, _name in USERS:
        print(f"  {email}")


if __name__ == "__main__":
    run_seeds()
