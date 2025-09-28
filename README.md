![CI](https://github.com/KoAt-DEV/multi-tenant-saas-starter/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## SaaS Starter – Multi‑Tenant FastAPI + Postgres

Production‑ready starter for building a multi‑tenant SaaS backend with FastAPI, PostgreSQL, and SQLAlchemy (async). It includes JWT auth, refresh tokens, role/permission RBAC, tenant resolution via middleware, Alembic migrations, seed scripts, and example endpoints with tests.

### Features
- Multi‑tenant resolution via `TenantMiddleware` using the HTTP Host header
- JWT access and refresh tokens, password reset flow
- Role/Permission RBAC with dependency guards
- Async SQLAlchemy + Alembic migrations
- Typed Pydantic schemas
- Seed script for demo data (tenants, users, roles, permissions)
- Docker and docker‑compose example with Traefik
- Pytest setup (async tests via httpx)

### Tech stack
- FastAPI, Starlette middleware
- SQLAlchemy 2.x (async) + asyncpg (PostgreSQL)
- Alembic for migrations
- python‑jose for JWT
- Pydantic / pydantic‑settings
- passlib[bcrypt] for password hashing
- Pytest, pytest‑asyncio, httpx

---

## Directory structure
```text
app/
  main.py                 # FastAPI app + routers + middleware
  config.py               # Settings via pydantic‑settings
  db.py                   # Async engine + session dependency
  middleware/tenant_middleware.py
  routers/                # auth, user, tenant, permission_check, debug
  services/               # auth utilities, RBAC helpers, tenant helper
  models/                 # SQLAlchemy models (users, tenants, roles, etc.)
  schemas/                # Pydantic schemas
alembic/                  # Alembic migration environment + versions/
scripts/seed_script.py    # Full demo data seed
tests/                    # Pytest tests and test helpers
Dockerfile, docker-compose.yml
requirements.txt, pytest.ini, alembic.ini
```

---

## Getting started

### Prerequisites
- Python 3.12+
- PostgreSQL 14+

### Setup (local)
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in project root:
```env
SECRET_KEY=change-me
DB_URL=postgresql+asyncpg://USER:PASSWORD@localhost:5432/saas_db
TEST_DB_URL=postgresql+asyncpg://USER:PASSWORD@localhost:5432/saas_db_test
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=14
DEFAULT_DEV_TENANT=public
DEFAULT_TEST_TENANT=client1
PROD_ENV=prod
TEST_ENV=test
```

### Database
Run migrations to create all tables:
```bash
alembic upgrade head
```

Seed demo data (tenants, users, roles, permissions):
```bash
python scripts/seed_script.py
```

### Run the API
```bash
uvicorn app.main:app --reload
```
The service starts at `http://127.0.0.1:8000`.

---

## Multi‑tenancy model
Tenant is resolved per request by `TenantMiddleware` using the `Host` header:
- In `PROD_ENV=prod`, requests to `localhost` automatically resolve to `DEFAULT_DEV_TENANT` (e.g., `public`).
- In non‑dev, subdomain (e.g., `client1.example.com`) or `custom_domain` must map to a tenant record.

When testing with curl in development, either:
- Use `localhost` (tenant falls back to `DEFAULT_DEV_TENANT`), or
- Set a `Host` header to match your tenant domain.

Example with header:
```bash
curl -H "Host: client1.local.com" http://127.0.0.1:8000/
```

---

## API overview

Root
- GET `/` → health: `{ "status": "ok" }`

Auth (`app/routers/auth.py`)
- POST `/api/auth/token` – OAuth2 Password flow (form fields `username`, `password`)
- POST `/api/auth/login` – Login returning access and refresh tokens (query params `email`, `password`)
- POST `/api/auth/refresh` – Refresh access/refresh token pair (body: `{ "refresh_token": "..." }`)
- POST `/api/auth/logout` – Revoke refresh token (body: `{ "refresh_token": "..." }`)
- POST `/api/auth/forgot-password` – Request password reset token
- POST `/api/auth/reset-password` – Reset password with token
- GET `/api/auth/me` – Returns current user info (user_name, user_email, tenant_name, roles) for the tenant of the logged-in user

Tenant data (`app/routers/tenant.py`)
- GET `/api/tenant/tenant-data` – Returns basic tenant info; requires `read` permission

Permission check (`app/routers/permission_check.py`)
- POST `/api/permission-check/admin-only` – Requires role `admin_tenant`


### Example flows

1) Obtain access token (OAuth2 form)
```bash
curl -X POST http://127.0.0.1:8000/api/auth/token \
  -H "Host: public.local.com" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@public.com&password=admin123"
```

2) Login for access + refresh tokens
```bash
curl -X POST "http://127.0.0.1:8000/api/auth/login?email=admin@public.com&password=admin123" \
  -H "Host: public.local.com"
```

3) Use access token
```bash
ACCESS=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
curl -H "Authorization: Bearer $ACCESS" -H "Host: public.local.com" \
  http://127.0.0.1:8000/api/tenant/tenant-data
```

4) Refresh
```bash
curl -X POST http://127.0.0.1:8000/api/auth/refresh \
  -H "Host: public.local.com" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh>"}'
```

---

## Testing

Install test deps (already in `requirements.txt`):
```bash
pip install -r requirements.txt
```

Set a dedicated test database in `.env` (or export before running tests):
```env
TEST_DB_URL=postgresql+asyncpg://USER:PASSWORD@localhost:5432/saas_db_test
```

Run tests:
```bash
pytest -q
```

Notes:
- Tests use async httpx client and may need the test DB schema created (`alembic upgrade head` on the test DB) before seeding.
- For endpoints requiring tenant resolution, ensure the `Host` header is set or `PROD_ENV=prod` with a `DEFAULT_DEV_TENANT`.

---

## Docker

Build and run with docker‑compose (includes Traefik example):
```bash
docker compose up --build
```

Traefik routes in `docker-compose.yml` demonstrate subdomain‑based tenant routing such as `public.local.com`.

---

## Security & production notes
- Use a strong `SECRET_KEY` and rotate if compromised
- Configure proper CORS origins under `app.main`
- Use HTTPS and secure cookies if serving tokens in the browser
- Scope roles/permissions to your domain model, keep permissions minimal
- Backup and apply migrations carefully between environments

---

## Troubleshooting
- Tenant not found: verify `Host` header and tenant records; in dev, `PROD_ENV=prod` + `DEFAULT_DEV_TENANT` fallback
- DB errors: confirm `DB_URL` connectivity; run `alembic upgrade head` and `scripts/seed_script.py`
- Test loop issues: ensure a single event loop per session and avoid DDL per test (truncate instead of drop/create)

---

## License
This project is licensed under the MIT License – see the [LICENSE](./LICENSE) file for details.


