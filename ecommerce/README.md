# Multi-Vendor AI E-commerce Platform

Graduation-project scaffold for a multi-vendor marketplace with three roles (Admin,
Seller, Customer) and a provider-agnostic AI layer.

## Stack

- Frontend: Node 22 LTS, Vue 3, TypeScript strict, Vite 8, Pinia, Vue Router, Tailwind CSS,
  Heroicons, Chart.js.
- Backend: Python 3.12, Django 5, Django REST Framework, Channels, Celery and Beat.
- Infrastructure: external PostgreSQL with `pg_trgm` and `pgvector`, Redis 7,
  Docker Compose and Nginx.
- AI/payment defaults: Google Gemini, `gemini-embedding-2` at 1536 dimensions,
  COD and VNPay Sandbox.

The architecture and non-negotiable rules are documented in
[`docs/PROJECT_CONSTITUTION.md`](docs/PROJECT_CONSTITUTION.md) and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Repository structure

```text
.
├── backend/
│   ├── apps/
│   │   ├── account/          # User profiles, JWT auth, RBAC and account services
│   │   └── common/           # Response, errors, audit, pagination, logging, health
│   ├── config/settings/      # base / development / production / test
│   ├── requirements/
│   └── Dockerfile
├── frontend/
│   ├── src/features/         # Domain-oriented Vue features
│   ├── src/shared/           # Cross-feature UI, HTTP and types
│   ├── src/router/           # Public/customer/seller/admin routes
│   ├── src/layouts/
│   └── Dockerfile
├── nginx/                    # Edge reverse proxy
├── docs/
├── docker-compose.yml
├── docker-compose.dev.yml
└── .env.example
```

## Prerequisites

- Docker Desktop with Docker Compose v2.
- A PostgreSQL server reachable from Docker. PostgreSQL is intentionally not part
  of `docker-compose.yml`.
- The database server must provide the `pg_trgm` and `vector` extensions.

Create a database/user using your normal PostgreSQL administration workflow, then
enable the required extensions in the target database:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;
```

For PostgreSQL running on the host machine, the example configuration uses
`host.docker.internal`. Replace `POSTGRES_HOST` when the database is hosted elsewhere.

## Environment setup

```bash
cp .env.example .env
```

At minimum, replace:

- `DJANGO_SECRET_KEY`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`
- `DJANGO_ALLOWED_HOSTS`, CORS/CSRF origins for non-local environments

`GEMINI_API_KEY` and `VNPAY_*` may stay empty until their feature groups are implemented.
Never commit `.env`.

## Run with Docker Compose

Production-like local stack:

```bash
docker compose up --build
```

Development stack with Django/Vite source mounts and hot reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Open:

- Application: <http://localhost:8080>
- Backend readiness: <http://localhost:8080/api/health/>
- OpenAPI UI: <http://localhost:8080/api/docs/>
- Vite directly in development: <http://localhost:5173>

Inspect health status:

```bash
docker compose ps
```

All six runtime services have healthchecks: frontend, backend, Celery worker,
Celery beat, Redis and edge Nginx.

## Database migration

Step 2 defines `AUTH_USER_MODEL` and includes the first migrations for the custom User,
three role profiles and AuditLog. Apply migrations before starting the application:

```bash
docker compose run --rm backend python manage.py migrate
```

Do not generate or apply an earlier migration that uses Django's default `auth.User`.

## Authentication and RBAC

- Public registration creates an unverified Customer and queues a verification email in Celery.
- Access JWTs live for 15 minutes and are kept in frontend memory only.
- Rotating refresh JWTs are stored in an `HttpOnly` cookie and blacklisted on rotation/logout.
- Password changes, password resets and role changes increment `token_version`, immediately
  invalidating previously issued access tokens.
- `/api/v1/users/me/` always derives identity from the authenticated token; it never accepts a
  client-provided `user_id`.
- `/api/v1/admin/users/{id}/assign-role/` requires Admin permission and writes an AuditLog.

Useful browser routes:

- `/auth/register`, `/auth/login`, `/auth/forgot-password`
- `/account/profile`
- `/seller` (Seller only)
- `/admin` and `/admin/roles` (Admin only)

## Local quality checks

Frontend (Node 22 LTS):

```bash
cd frontend
npm ci
npm run lint
npm run test
npm run build
```

Backend (Python 3.12):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/development.txt
ruff check .
python manage.py check
pytest
```

These jobs are mirrored in `.github/workflows/ci.yml`. Core modules added later
(cart, checkout, voucher and inventory) must reach at least 60% coverage; inventory
must also include a concurrent oversell test.

## Service routing

```text
Browser -> Nginx :8080
            ├── /             -> Vue frontend
            ├── /api/*        -> Django ASGI backend
            ├── /ws/*         -> Django Channels
            ├── /static/*     -> shared static volume
            └── /media/*      -> shared media volume

Backend / Celery / Channels -> Redis
Backend / Celery            -> external PostgreSQL via environment variables
```

## Next implementation step

Step 3 reviews the remaining mandatory requirement codes and agrees on a dependency-ordered
delivery roadmap before another feature group is implemented.
