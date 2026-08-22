# Austial/Swadely Testing Scripts

Quick-start scripts for testing the platform.

## Available Scripts

### `test-quick.sh`
**Quick full test suite** — runs backend unit/integration tests, frontend tests, type checking, and linting.

```bash
./scripts/test-quick.sh
```

**What it tests:**
- ✅ Backend unit tests
- ✅ Backend integration tests  
- ✅ Frontend unit tests
- ✅ Backend type checking (mypy)
- ✅ Backend linting (ruff)

**Duration:** ~2-5 minutes depending on machine

---

### `test-phase8-9.sh`
**Phase 8 & 9 focused tests** — tests newly completed Compliance & Reporting + AI/ML features.

```bash
./scripts/test-phase8-9.sh
```

**What it tests:**
- ✅ AML alert service (Phase 8)
- ✅ Compliance report generation (Phase 8)
- ✅ Audit log immutability (Phase 8)
- ✅ KYC ML service: OCR, liveness, face matching (Phase 9)
- ✅ AML scoring service (XGBoost) (Phase 9)
- ✅ Valuation anomaly detection (Phase 9)
- ✅ ML prediction audit trail (Phase 9)
- ✅ Compliance → ML integration tests
- ✅ API endpoint registration

**Duration:** ~1-2 minutes

---

## Detailed Testing Guide

For comprehensive phase-by-phase testing instructions with curl examples, see **[`../TESTING.md`](../TESTING.md)**.

Covers:
- Phase 1-9 manual API testing
- KYC submission → allocation → redemption workflows
- Compliance report generation
- ML model training & integration
- Load testing, security testing, CI/CD setup

---

## Prerequisites

**Backend:**
```bash
cd backend/
uv sync
cp .env.example .env.test
# Edit .env.test with test database credentials
```

**Frontend:**
```bash
cd frontend/
npm install
```

**Services:**
```bash
# Start PostgreSQL + Redis
docker compose -f docker-compose.test.yml up -d

# Apply migrations
cd backend/
uv run alembic upgrade head
```

---

## Individual Test Commands

**Backend unit tests:**
```bash
cd backend/
uv run pytest tests/unit/ -v
```

**Backend integration tests:**
```bash
uv run pytest tests/integration/ -v
```

**Backend with coverage:**
```bash
uv run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

**Frontend tests:**
```bash
cd frontend/
npm test
```

**Frontend e2e:**
```bash
npm run e2e
```

**Type checking:**
```bash
cd backend/
uv run mypy src/
```

**Linting:**
```bash
uv run ruff check src/
uv run ruff format src/  # auto-fix
```

---

## CI/CD

These scripts are designed to run in CI/CD pipelines. See `.github/workflows/test.yml` for GitHub Actions setup.

**Run all checks locally (mimics CI):**
```bash
./scripts/test-quick.sh
```
