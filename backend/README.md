<div align="center">
  <img src="assets/swadely-logo.png" alt="Swadely" width="360" />

  <h3>Swadely Backend API</h3>
  <p>Cross-border payments &amp; real-world-asset tokenization, built for GIFT City / IFSCA.</p>

  <p>
    <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+" />
    <img src="https://img.shields.io/badge/framework-Austial-2E5339" alt="Austial framework" />
    <img src="https://img.shields.io/badge/built%20on-FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/database-PostgreSQL-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
    <img src="https://img.shields.io/badge/package%20manager-uv-DE5FE9" alt="uv" />
    <img src="https://img.shields.io/badge/status-active%20development-yellow" alt="Active development" />
    <img src="https://img.shields.io/badge/region-GIFT%20City%20%2F%20IFSCA-0B4F6C" alt="GIFT City / IFSCA" />
    <img src="https://img.shields.io/badge/license-proprietary-lightgrey" alt="Proprietary license" />
  </p>
</div>

---

## Table of contents

- [About](#about)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Background jobs (Celery + Redis)](#background-jobs-celery--redis)
- [Object storage](#object-storage)
- [API endpoints](#api-endpoints)
- [Generating more artifacts](#generating-more-artifacts)
- [Testing](#testing)
- [Code quality & pre-commit hooks](#code-quality--pre-commit-hooks)
- [Roadmap](#roadmap)
- [License](#license)

## About

`api.swadely.com` is the production backend for **Swadely**, a GIFT City
(India IFSC/IFSCA-regulated) cross-border payments and real-world-asset (RWA)
tokenization platform. It's built as a consumer application on top of
[Austial](https://github.com/), a NestJS-style, batteries-included web
framework for Python built on FastAPI, and is scaffolded via the Austial CLI
(`austial new`).

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Framework | [Austial](https://github.com/) (NestJS-style DI, decorators, modules) on FastAPI |
| Database | PostgreSQL, via `austial-orm` |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| Testing | pytest, pytest-asyncio, httpx (ASGI transport, no mocked HTTP layer) |
| Lint / format / types | ruff, mypy |
| Git hooks | pre-commit (lint + format + type-check on commit, tests on push) |

## Project structure

```
src/
├── main.py                  # entry point (mirrors Nest's main.ts)
├── app_module.py             # root module (mirrors app.module.ts)
├── app_controller.py
├── app_service.py
└── modules/
    └── health/                # GET /health, GET /health/protected
        └── guards/
            └── api_key_guard.py
tests/
├── unit/                    # provider-level tests, resolved from the DI container
└── e2e/                     # full ASGI-transport HTTP tests, no mocking
```

> Note: Python can't import filenames containing dots the way Node resolves
> `health.controller.ts`, so Austial uses `health_controller.py` /
> `health_service.py` / `health_module.py` instead -- same one-folder-per-feature
> layout as Nest, just underscore-suffixed file names.

## Getting started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- A reachable PostgreSQL server
- A reachable Redis server (Celery broker + result backend -- see
  [Background jobs (Celery + Redis)](#background-jobs-celery--redis))
- AWS credentials + a private S3 bucket for KYC/disclosure document storage
  in production (see [Object storage](#object-storage)) -- not required just
  to run the test suite, which fakes S3 via `moto`

The fastest way to get Postgres + Redis + the API + a worker all running
together locally is `docker compose up --build` (see `docker-compose.yml`).

### Install

```bash
uv sync
cp .env.example .env   # then fill in DATABASE_URL, API_KEY, PORT, REDIS_URL, DOCUMENTS_S3_BUCKET, AWS_REGION
```

### Database migrations (Alembic)

Schema is owned entirely by `alembic/` migrations -- `synchronize=False` is
permanent for the app's real `OrmModule.for_root_async(...)` (see
`src/app_module.py`; tests still use a disposable in-memory
`synchronize=True` SQLite `DataSource`, which is unrelated). Every entity
change ships with a migration in the same unit of work -- see
`alembic/README.md` for the full rule and commands:

```bash
uv run alembic upgrade head                                    # apply pending migrations
uv run alembic revision --autogenerate -m "<short description>" # after adding/changing an entity
```

### Run

```bash
uv run austial serve          # http://localhost:8000, auto-reload
# or
uv run python -m src.main
```

> **Always prefix with `uv run`.** A bare `austial` on your `$PATH` may resolve
> to a globally `uv tool install`ed copy in an isolated environment, not this
> project's own `.venv` with its local editable framework packages -- that
> mismatch surfaces as `ModuleNotFoundError: No module named 'austial.orm'`.

## Background jobs (Celery + Redis)

`src/jobs/celery_app.py` configures one `Celery` app against `REDIS_URL` as
both broker and result backend (`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`
are optional overrides for the day those need to split from `REDIS_URL`).
`JobsModule` registers the same instance into the Austial DI container under
the `CELERY_APP` token for anything that needs to enqueue a task in-process.

```bash
uv run celery -A src.jobs.celery_app worker --loglevel=info   # run a worker
```

`src/jobs/tasks.py` currently has one placeholder (`jobs.health_check`)
proving the seam works end-to-end -- no real domain task bodies (sanctions
re-screening, valuation polling, etc.) exist yet; those land with their
owning Phase 2+ domain modules. `tests/unit/jobs_spec.py` exercises task
registration/config plus an eager (in-process, no live broker) execution
path; a real worker consuming from a live Redis is exercised manually via
the command above, not in the automated suite.

**Deployment note:** this app's cost-capped single-EC2-instance deployment
(see `austial-hackathon/infra/terraform/README.md`) has no managed Redis --
Redis and a Celery worker process both need to run as additional plain
containers alongside the existing backend container on that same instance.

## Object storage

`src/storage/object_storage_service.py`'s `ObjectStorageService` (registered
by `StorageModule`) generates short-lived presigned S3 upload/download URLs
for KYC documents and disclosure PDFs -- callers upload/download bytes
directly against S3; the API process never proxies file bytes, and no
document is ever stored as a DB blob (only its object key/URL is referenced
on whatever entity owns it, starting in Phase 2+). Configured via
`DOCUMENTS_S3_BUCKET` and `AWS_REGION`.

**Deployment note:** production needs a **new, private, encrypted-at-rest**
S3 bucket, separate from the existing public frontend static-website bucket
(Terraform follow-up, not provisioned here). Also note: real IFSCA rules
require GIFT IFSC-resident storage; this demo runs in AWS `us-east-1`, which
satisfies the *architecture* (private, encrypted, referenced-not-embedded)
but not the literal data-residency requirement -- a known, already-tracked
gap in the demo deployment.

## API endpoints

| Method | Path | Description | Guard |
|---|---|---|---|
| `GET` | `/` | Root route, returns a welcome message | none |
| `GET` | `/health` | Terminus-style health check (memory heap + database) | none |
| `GET` | `/health/protected` | Same as above, requires `x-api-key: <API_KEY from .env>` | `ApiKeyGuard` |
| `GET` | `/docs` | Swagger UI (free from FastAPI) | none |
| `POST` | `/auth/register` | Register a new user (always created as `INVESTOR`) | none |
| `POST` | `/auth/login` | Exchange credentials for an access/refresh token pair | none |
| `POST` | `/auth/refresh` | Exchange a refresh token for a new token pair | none |
| `POST` | `/auth/logout` | Revoke a refresh token | none |
| `GET` | `/admin/dashboard/summary` | Investor count / pending-KYC count / users-by-role aggregates | `JwtAuthGuard` + `RolesGuard(ADMIN, COMPLIANCE_OFFICER)` |
| `GET` | `/admin/users` | Paginated user list, `?search=`/`?skip=`/`?take=` | `JwtAuthGuard` + `RolesGuard(ADMIN)` |
| `PATCH` | `/admin/users/:id/role` | Change a user's role (audit-logged) | `JwtAuthGuard` + `RolesGuard(ADMIN)` |
| `PATCH` | `/admin/users/:id/suspend` | Suspend a user account (audit-logged) | `JwtAuthGuard` + `RolesGuard(ADMIN)` |

## Generating more artifacts

```bash
uv run austial generate module cats
uv run austial generate controller cats
uv run austial generate service cats
uv run austial generate resource cats   # module + CRUD controller + service + dto
```

## Testing

```bash
uv run pytest
```

Unit and e2e specs build their providers/app straight from the DI container
via `austial.testing`, and wire an in-memory SQLite `DataSource` instead of
the real Postgres one -- this keeps the suite hermetic and fast, with zero
dependency on a live database, while still exercising real `austial-orm`
code paths (including `DatabaseHealthIndicator`'s ping check). The running
app itself always talks to the real PostgreSQL server configured via
`DATABASE_URL`.

## Code quality & pre-commit hooks

```bash
uv run ruff check .      # lint
uv run ruff format .     # format
uv run mypy src tests    # type-check

uv run pre-commit install --hook-type pre-commit --hook-type pre-push
uv run pre-commit run --all-files   # run every hook once, on demand
```

Once installed, `git commit` runs formatting/linting/type-checks automatically,
and `git push` also runs the test suite -- mirroring a typical Nest project's
husky + lint-staged setup.

## Roadmap

- [x] Bootstrap via `austial new`, linked to the local `austial-py` framework checkout
- [x] Health module with memory + PostgreSQL indicators
- [x] AuthN/AuthZ (`/auth/*`, JWT + refresh tokens, role-based guards)
- [x] Alembic migrations (schema owned by `alembic/`, `synchronize=False` in production)
- [x] Background jobs seam (Celery + Redis, no domain task bodies yet)
- [x] Object storage seam (presigned S3 URLs for KYC/disclosure documents)
- [x] Admin panel backend (`/admin/*` -- dashboard summary, user management, audit-logged role/suspend changes)
- [ ] Payments domain module (cross-border settlement)
- [ ] RWA tokenization domain module
- [ ] KYC / onboarding module (submission endpoints, consumes the object storage seam above)

## License

Proprietary -- © Swadely. All rights reserved. Not licensed for external use,
reproduction, or distribution without prior written permission.
