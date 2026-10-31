<div align="center">

# 📸 insta.crm

### Multi-tenant CRM for Instagram DMs

Connect your Instagram Professional accounts, sync contacts and conversations, and manage them with your team — one workspace per company, with plan-based feature gating and role-based access.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?logo=postgresql&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.4-37814A?logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?logo=typescript&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

---

## Table of contents

- [Overview](#overview)
- [Features](#features)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Connecting Instagram](#connecting-instagram)
- [API reference](#api-reference)
- [Data model](#data-model)
- [Background jobs](#background-jobs)
- [Web app](#web-app)
- [CLI reference](#cli-reference)
- [Testing](#testing)
- [Extending the codebase](#extending-the-codebase)
- [Deployment](#deployment)
- [Roadmap](#roadmap)
- [License](#license)

---

## Overview

**insta.crm** is a SaaS-style CRM built around Instagram direct messages. Agencies, creators and businesses can plug in one or more Instagram Professional accounts, import every DM thread as a **contact** and **conversation**, and receive new messages live through Meta webhooks.

It is **multi-tenant by design**: users are global, *companies* (tenants) are isolated workspaces, and a user can belong to many companies with a different role in each. Tenant isolation is enforced both in the application layer and by the database itself (composite foreign keys).

The backend follows a **Rails-like convention layout** (controllers with `before_action` filters, models with lifecycle callbacks, services, jobs, a single routes file, and a `manage.py` CLI with generators) on top of FastAPI and SQLAlchemy 2.0.

## Features

| Area | What you get |
|------|--------------|
| 🔐 **Authentication** | JWT access + refresh tokens, bcrypt password hashing, `/auth/me` |
| 🏢 **Multi-tenancy** | Companies as isolated workspaces; users join many companies via memberships |
| 🛡️ **RBAC** | System roles (owner, admin, manager, agent, viewer) mapped to fine-grained permissions such as `conversations.reply` |
| 💳 **Plans & entitlements** | Starter / Pro plans with feature flags and numeric limits (e.g. `instagram_accounts`); sidebar adapts to the plan |
| 📲 **Instagram OAuth connect** | Instagram Login flow with CSRF-safe signed `state`; plan limit enforced |
| 🔑 **Manual connect** | Verify a profile with an access token, get a per-account webhook URL + verify token |
| 🔒 **Encrypted tokens** | Access tokens encrypted at rest (`ENCRYPTION_KEY`) and never returned by the API |
| 📥 **Webhooks** | `GET` handshake + `POST` delivery, `X-Hub-Signature-256` HMAC verification, idempotent event storage |
| 🔄 **Contact & conversation sync** | Background Celery job imports DM threads into contacts, conversations and messages |
| 🖥️ **React web app** | Login, collapsible sidebar, Channels, Contacts, Conversations, plan-aware navigation |
| 🧪 **Tests** | Pytest suite covering auth, channels, webhooks, sync, filters and model callbacks |

## Tech stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| API | FastAPI, Uvicorn |
| ORM / Migrations | SQLAlchemy 2.0, Alembic (timestamped migrations) |
| Validation | Pydantic v2, pydantic-settings |
| Database | PostgreSQL 15+ (SQLite in-memory for tests) |
| Queue / Cache | Redis, Celery (queues: `default`, `mailers`, `critical`, `low_priority`) |
| Auth | python-jose (JWT), bcrypt |
| Frontend | React 18, TypeScript, React Router 6, Vite 5 |
| CLI | Click (`manage.py`) |
| Testing | Pytest, HTTPX |

## Architecture

```
┌──────────────┐   /api (proxy)   ┌───────────────────────────────────────┐
│  React + Vite │ ───────────────▶ │  FastAPI                              │
│  (port 3000)  │ ◀─────────────── │  Middleware → Controllers → Services  │
└──────────────┘                   │                 │            │        │
                                   │             Models (ORM)  Jobs (enqueue)
┌──────────────┐  webhooks / OAuth │                 │            │        │
│ Instagram /  │ ───────────────▶  └─────────────────┼────────────┼────────┘
│ Meta Graph   │ ◀───────────────                    ▼            ▼
└──────────────┘   API calls            ┌────────────────┐   ┌────────────────┐
        ▲                               │  PostgreSQL    │   │ Redis (broker) │
        │                               └────────────────┘   └───────┬────────┘
        │                                                            ▼
        └──────────────────────────────────────────────────  Celery worker
                                                           (InstagramSyncJob)
```

**Request lifecycle:** `config/routes.py` registers each endpoint through `route()` / `resources()`. A wrapper builds the controller, runs its `before_action` filters (authenticate, load membership, check permission), calls the action, then runs `after_action` filters. Business logic lives in **services**; persistence goes through **models**; slow work is pushed to **Celery jobs**.

**Layers**

- **Controllers** — `BaseController` with `params`, `render_json()`, `render_error()` and filters (`@before_action`, `@after_action`, `@skip_before_action`). Concerns: `Authenticatable`, `TenantScoped` (loads the membership for `{company_id}` and checks permissions), `Paginatable`.
- **Models** — `BaseModel` with callbacks (`@before_save`, `@after_create`, …), `find / find_by / where / create / save / update / destroy`. Mixins: `Timestampable`, `SoftDeletable`, `Sluggable`, `StandardColumns`.
- **Services** — `BaseService` (`success()` / `failure()`). Key services: `AuthService`, `EntitlementService`, `InstagramService`, `InstagramSyncService`, plus `InstagramClient` (thin Graph API HTTP client).
- **Jobs** — `BaseJob` with `perform_later`, `perform_now`, retries and queues. `InstagramSyncJob` runs the DM import.
- **Helpers** — `jwt_helper`, `password_helper`, `crypto_helper` (token encryption), `response_helper`.
- **Middleware** — `auth_middleware` (JWT → `request.state.current_user`) and `logging_middleware`.

## Project structure

```
insta-crm/
├── main.py                     # FastAPI app, CORS, lifespan, /health
├── manage.py                   # CLI: runserver, db, generate, routes, worker, scheduler, shell
├── alembic.ini
├── requirements.txt
├── .env.example
│
├── config/
│   ├── settings.py             # Pydantic Settings (.env)
│   ├── database.yml(.example)  # Per-environment DB config
│   ├── database_yml.py         # Builds DATABASE_URL from database.yml
│   ├── database.py             # Engine, SessionLocal, Base, get_db
│   ├── celery.py               # Celery app, queues, task registration
│   └── routes.py               # route(), resources(), namespace(), draw_routes()
│
├── app/
│   ├── controllers/            # auth, companies, channels, contacts, conversations
│   │   └── concerns/           # authenticatable, tenant_scoped, paginatable
│   ├── models/                 # User, Tenant, TenantMembership, Plan, SocialAccount,
│   │   │                       # InstagramConnection, Contact, Conversation, Message, WebhookEvent
│   │   └── concerns/           # timestampable, soft_deletable, sluggable, standard_columns
│   ├── services/               # auth, entitlement, instagram, instagram_sync, instagram_client
│   ├── jobs/                   # base_job, instagram_sync_job
│   ├── schemas/                # Pydantic request/response schemas
│   ├── middleware/             # auth, logging
│   └── helpers/                # jwt, password, crypto, response
│
├── db/
│   ├── migrations/versions/    # 38 timestamped Alembic migrations
│   └── seeds.py                # Roles, permissions, plans, demo companies and users
│
├── tests/                      # Pytest suite
├── scripts/                    # Manual test helpers
│
└── web/                        # React + TypeScript + Vite frontend
    └── src/
        ├── api/client.ts       # Fetch wrapper with token refresh
        ├── auth/               # AuthContext, RequireAuth
        ├── layout/             # CompanyLayout, Sidebar, nav (plan-aware)
        ├── pages/              # Login, Home, Channels, Contacts, Conversations, …
        └── components/         # Avatar, …
```

## Quick start

**Prerequisites:** Python 3.11+, PostgreSQL 15+, Redis, Node.js 18+.

```bash
# 1. Backend setup
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
cp config/database.yml.example config/database.yml   # edit credentials

# 2. Database
python manage.py db migrate
python manage.py db seed             # roles, plans, 2 demo companies, 4 demo users

# 3. Run the API
python manage.py runserver           # http://localhost:8000
```

```bash
# 4. Run the web app (new terminal)
cd web && npm install && npm run dev # http://localhost:3000  (proxies /api → :8000)
```

```bash
# 5. Run the background worker (new terminal, venv active) — needed for DM sync
redis-cli ping                       # -> PONG
python manage.py worker
```

Open **http://localhost:3000** and sign in. API docs are at **http://localhost:8000/docs** when `DEBUG=true`.

### Demo accounts

All seeded users share the password `Password@123` (override with `SEED_PASSWORD`). **Development only.**

| User | Email | Companies (role) |
|------|-------|------------------|
| Rahul Verma | `rahul@rahulfitness.demo` | Rahul Fitness (owner) |
| Priya Singh | `priya@rahulfitness.demo` | Rahul Fitness (agent) |
| Aman Gupta | `aman@techwithaman.demo` | Tech With Aman (owner) |
| Rohit Kushwaha | `rohit@agency.demo` | Rahul Fitness (admin), Tech With Aman (agent) |

Seeded plans: **Starter** (₹999/mo — 1 Instagram account, 3 members, inbox/contacts/leads) and **Pro** (₹2999/mo — 5 accounts, 10 members, all features).

> There is no public signup yet; users are created by seeds (invitations are planned).

## Configuration

Copy `.env.example` to `.env`.

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | `development` / `staging` / `production` | `development` |
| `DEBUG` | Enables `/docs`, `/redoc` | `true` |
| `SECRET_KEY` | App secret | — |
| `DATABASE_URL` | Overrides `config/database.yml` | from YAML |
| `JWT_SECRET_KEY` / `JWT_ALGORITHM` | JWT signing (also signs the OAuth `state`) | — / `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | `7` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Celery broker / results | `redis://…/1` / `…/2` |
| `FRONTEND_URL` | Where the OAuth callback redirects the browser | `http://localhost:3000` |
| `INSTAGRAM_APP_ID` / `INSTAGRAM_APP_SECRET` | Instagram app credentials (from the *Instagram* product, not Settings → Basic) | — |
| `INSTAGRAM_REDIRECT_URI` | Public `https` URL ending in `/api/v1/channels/instagram/callback` | — |
| `INSTAGRAM_VERIFY_TOKEN` | Webhook verify token (must match Meta app) | — |
| `ENCRYPTION_KEY` | Encrypts stored access tokens | — |
| `SUBSCRIPTION_ENFORCED` | When `false`, every active company counts as subscribed | `false` |
| `CORS_ORIGINS` | Allowed browser origins | `localhost:3000` |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | Pagination | `20` / `100` |

Database settings live in `config/database.yml` (`default` + `development` / `test` / `production` sections), selected by `APP_ENV`.

## Connecting Instagram

Two ways to connect an account, both from the **Channels** page. Only members with `settings.manage` (owner/admin) can connect or disconnect, and the plan's `instagram_accounts` limit is enforced.

### Option A — OAuth ("Connect to Instagram")

1. User clicks **Connect to Instagram**; the API creates a signed, 10‑minute `state` (user + company) and redirects to Instagram.
2. After login, Instagram redirects to `/api/v1/channels/instagram/callback?code&state`.
3. The API verifies `state`, exchanges the code for a long-lived token (60 days), stores the account and the **encrypted** token, then redirects to `FRONTEND_URL`.

### Option B — Manual connect

1. `verify` — submit the Instagram app/user ID and an access token; the API checks the profile.
2. `webhook-preview` — issues a **per-account webhook URL and verify token**.
3. `connect` — stores the connection with the token encrypted.

### One-time platform setup (Meta)

1. In the Meta app (developers.facebook.com) add the **Instagram** product → *API setup with Instagram login*, and copy the **Instagram app ID/secret** into `.env`.
2. Add the OAuth redirect URI `<public API URL>/api/v1/channels/instagram/callback` under *Business login settings* and set the same value in `INSTAGRAM_REDIRECT_URI`.
3. Generate an encryption key and set `ENCRYPTION_KEY` (never change it without re-encrypting stored tokens):
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
4. Configure the webhook callback `<public API URL>/api/v1/channels/instagram/webhook` with the same `INSTAGRAM_VERIFY_TOKEN`, and subscribe to `messages`.
5. While the Meta app is in **Development mode**, add each account under *App roles → Instagram testers* and accept the invite. Accounts must be **Professional** (Business/Creator).

**Local development:** Meta must reach your machine, so expose the API with a tunnel (`ngrok http 8000`) and use the `https` URL in `INSTAGRAM_REDIRECT_URI` and in the Meta app. Free ngrok URLs change on restart — update both places.

### Webhook security

- `GET` handshake validates the verify token.
- `POST` deliveries are verified with `X-Hub-Signature-256` (HMAC‑SHA256 using `INSTAGRAM_APP_SECRET`).
- Each delivery is stored in `webhook_events` keyed by a hash of the body, so Meta retries are **idempotent**.

## API reference

Base path: `/api/v1`. Authenticated endpoints expect `Authorization: Bearer <access_token>`. Company-scoped endpoints verify the caller is a member of `{company_id}` (UUID).

### Auth & companies

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `POST` | `/auth/login` | – | `{email, password}` → access + refresh JWT, user, companies |
| `POST` | `/auth/refresh` | – | `{refresh_token}` → new token pair |
| `GET` | `/auth/me` | ✅ | Current user and companies |
| `GET` | `/companies` | ✅ | Companies the user belongs to |
| `GET` | `/companies/{id}` | ✅ | Company, my roles, plan, enabled features (404 if not a member) |

### Channels (Instagram)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/companies/{id}/channels` | Channel summary, plan limit, connected accounts, `can_manage` |
| `POST` | `/companies/{id}/channels/instagram/connect` | Start OAuth connect / save a manual connection |
| `POST` | `/companies/{id}/channels/instagram/verify` | Verify an account + token |
| `POST` | `/companies/{id}/channels/instagram/webhook-preview` | Issue per-account webhook URL + verify token |
| `DELETE` | `/companies/{id}/channels/instagram/{account_id}` | Disconnect an account |
| `GET` | `/channels/instagram/callback` | OAuth redirect target (signed `state`, no Bearer) |
| `GET`/`POST` | `/channels/instagram/webhook[/{connection_id}]` | Meta webhook verify / delivery (no Bearer) |

### Contacts & conversations

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/companies/{id}/contacts` | Paginated contacts |
| `POST` | `/companies/{id}/contacts/instagram/{connection_id}/sync` | Enable sync and enqueue the import job |
| `GET` | `/companies/{id}/conversations` | Paginated conversations |
| `GET` | `/companies/{id}/conversations/{conversation_id}` | Conversation with messages |

All errors use a uniform JSON envelope from `response_helper`.

## Data model

PostgreSQL schema with **36 tables** across 38 migrations (extensions + `set_updated_at()` trigger included). Requires PostgreSQL 15+.

| Module | Tables |
|--------|--------|
| Identity & tenancy | `users`, `user_profiles`, `tenants`, `tenant_memberships`, `tenant_member_profiles`, `roles`, `permissions`, `role_permissions`, `membership_roles`, `invitations` |
| Plans & billing | `plans`, `features`, `plan_features`, `subscriptions`, `subscription_items`, `billing_events`, `tenant_feature_overrides`, `tenant_settings` |
| Instagram | `social_accounts`, `social_account_tokens`, `social_account_assignments`, `webhook_events`, `instagram_connections` |
| CRM | `contacts`, `conversations`, `messages`, `message_attachments`, `conversation_assignments`, `leads`, `lead_assignments`, `tags`, `contact_tags` |
| Automation, usage, audit | `automation_rules`, `automation_runs`, `ai_usage_records`, `usage_counters`, `audit_logs` |

**Design rules**

- **Users are global, tenants are companies.** Roles attach to the *membership*, never to the user.
- **Instagram senders are `contacts`, not users**, unique per `(social_account_id, platform_user_id)`.
- **Database-enforced isolation:** composite FKs such as `(tenant_id, contact_id) → contacts(tenant_id, id)` make cross-tenant references impossible.
- **Every table** has `additional_attributes JSONB`, `created_at`, and trigger-maintained `updated_at`.
- **Postgres features:** partial unique indexes (one live subscription per tenant, one open assignment per conversation), GIN `jsonb_path_ops`, `pg_trgm` search, full-text index on `messages.content`, BRIN on `audit_logs.created_at`, CHECK constraints, and idempotency keys.

**Roles & permissions** (seeded): `owner` (all) · `admin` (all except billing) · `manager` · `agent` · `viewer`, over permissions `contacts.read/write`, `conversations.read/reply`, `leads.manage`, `team.manage`, `billing.manage`, `settings.manage`.

## Background jobs

Jobs run in a **separate Celery worker**, with Redis as broker. Enabling sync only flips a flag and enqueues `InstagramSyncJob`; the worker then fetches the DM threads from Instagram and upserts contacts, conversations and messages, updating `sync_status` (`queued → running → synced | failed`).

```bash
python manage.py worker                    # default queue
python manage.py worker --queue=mailers    # another queue
python manage.py scheduler                 # Celery Beat (periodic tasks)
```

```python
from app.jobs.instagram_sync_job import InstagramSyncJob
InstagramSyncJob.perform_later(connection_id="...")   # queued in Redis
InstagramSyncJob.perform_now(connection_id="...")     # inline, no worker
```

Modules in `app/jobs/` are auto-registered; restart the worker after changes. On macOS `manage.py worker` uses `--pool=solo` (prefork crashes there).

## Web app

React 18 + TypeScript + Vite, with the dev server proxying `/api` to `:8000`.

- **Auth:** `AuthContext` + `RequireAuth`, automatic token refresh in `api/client.ts`.
- **Routing:** after login you land on `/accounts/companies/<company-id>` — the tenant is always in the URL.
- **Plan-aware sidebar:** items (Inbox, Leads, Campaigns, Automation, Analytics…) appear only when the plan enables the feature.
- **Pages:** Login, Home, **Channels** (connect/disconnect, webhook setup, sync), **Contacts**, **Conversations**; other sections render a placeholder.

```bash
cd web
npm run dev       # development
npm run build     # type-check + production build
```

## CLI reference

```bash
python manage.py <command>
```

| Group | Commands |
|-------|----------|
| Server | `runserver [--host] [--port]` |
| Database | `db migrate` · `db rollback [--step=N \| --to=REV]` · `db status` · `db history` · `db seed` · `db reset` |
| Generators | `generate migration\|controller\|model\|job\|service <name>` |
| Workers | `worker [--queue=NAME]` · `scheduler` |
| Utilities | `routes` (list all routes) · `shell` (REPL with `db` and all models) |

## Testing

Tests run against in-memory SQLite with a `db` session fixture and a `client` (TestClient with overridden `get_db`).

```bash
pytest tests/ -v

# with coverage
pip install pytest-cov
pytest tests/ -v --cov=app --cov-report=term-missing
```

Covered: health, auth API, channels, Instagram webhooks, sync, controller filters, route wrapper and model callbacks.

## Extending the codebase

```bash
python manage.py generate model article
python manage.py generate migration create_articles_table
python manage.py generate controller articles
python manage.py generate service article
```

1. **Model** → `app/models/<name>.py`, then export it from `app/models/__init__.py` (single import point: `from app.models import …`).
2. **Migration** → edit the generated file, then `python manage.py db migrate`.
3. **Controller + route** → add the route in `config/routes.py` with `route()` or `resources()`.
4. **Service / Job** → keep business logic in `app/services/`, slow work in `app/jobs/`.

Conventions: CRUD goes through models, schemas are for validation/serialization, and **all routes live in `config/routes.py`**.

## Deployment

1. Set `APP_ENV=production`, `DEBUG=false`, strong `SECRET_KEY`, `JWT_SECRET_KEY` and `ENCRYPTION_KEY`, and production DB/Redis/Celery URLs.
2. Run the API: `gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000`
3. Run one or more Celery workers (and Beat if you add periodic tasks) under systemd/supervisor.
4. `python manage.py db migrate` (seed only roles/plans; do not ship demo users).
5. Build the frontend (`cd web && npm run build`) and serve `web/dist` behind HTTPS; restrict `CORS_ORIGINS`.
6. Use a stable public HTTPS URL for the Instagram redirect URI and webhook.

## Roadmap

- [ ] Team invitations (replacing seed-only users)
- [ ] Inbox: reply to DMs from the CRM
- [ ] Leads pipeline, tags and assignments UI
- [ ] Campaigns and automation rules
- [ ] AI-assisted replies and usage metering
- [ ] Billing integration and subscription enforcement
- [ ] Analytics dashboard

The database schema already includes tables for most of these modules.

## License

Released under the [MIT License](LICENSE).
