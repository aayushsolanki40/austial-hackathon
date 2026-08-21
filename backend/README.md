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

### Install

```bash
uv sync
cp .env.example .env   # then fill in DATABASE_URL, API_KEY, PORT
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

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Root route, returns a welcome message |
| `GET` | `/health` | Terminus-style health check (memory heap + database) |
| `GET` | `/health/protected` | Same as above, requires `x-api-key: <API_KEY from .env>` |
| `GET` | `/docs` | Swagger UI (free from FastAPI) |

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
- [ ] Payments domain module (cross-border settlement)
- [ ] RWA tokenization domain module
- [ ] KYC / onboarding module
- [ ] AuthN/AuthZ beyond the static `x-api-key` guard

## License

Proprietary -- © Swadely. All rights reserved. Not licensed for external use,
reproduction, or distribution without prior written permission.
