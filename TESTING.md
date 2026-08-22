# Austial/Swadely Platform Testing Guide

Complete testing instructions for all 9 build phases of the Swadely RWA tokenization and cross-border payments platform.

## 🌐 Production Environment

**Live Deployment (AWS):**
- **Backend API:** `http://52.6.51.39:8000`
- **Frontend:** `http://austial-demo-frontend-459141725579.s3-website-us-east-1.amazonaws.com`
- **Region:** `us-east-1`
- **AWS Account:** `459141725579`

All curl examples in this guide use the production URLs. To test against a local environment, replace `http://52.6.51.39:8000` with `http://localhost:8000`.

**Quick test:**
```bash
# Test production API
curl http://52.6.51.39:8000/health

# Expected: {"status": "ok", "checks": {"memory_heap": {...}, "database": {...}}}
```

---

## Table of Contents

- [Quick Start](#quick-start)
- [Test Environment Setup](#test-environment-setup)
- [Phase 1: Foundation](#phase-1-foundation)
- [Phase 2: Identity & KYC](#phase-2-identity--kyc)
- [Phase 3: Issuers, Custodians, Assets](#phase-3-issuers-custodians-assets)
- [Phase 4: Issuance Workflow](#phase-4-issuance-workflow)
- [Phase 5: Ledger & Funding](#phase-5-ledger--funding)
- [Phase 6: Subscription & Allocation](#phase-6-subscription--allocation)
- [Phase 7: Valuation, Redemption, Distribution](#phase-7-valuation-redemption-distribution)
- [Phase 8: Compliance & Reporting](#phase-8-compliance--reporting)
- [Phase 9: AI/ML Layer](#phase-9-aiml-layer)
- [Integration Testing](#integration-testing)
- [Performance Testing](#performance-testing)
- [Security Testing](#security-testing)

---

## Quick Start

```bash
# Backend unit tests
cd backend/
uv run pytest

# Backend with coverage
uv run pytest --cov=src --cov-report=html

# Frontend unit tests
cd frontend/
npm test

# Frontend e2e tests
npm run e2e

# Run everything
./scripts/test-all.sh  # if exists
```

---

## Test Environment Setup

### Prerequisites

```bash
# Backend
cd backend/
uv sync
cp .env.example .env.test

# Configure .env.test
DATABASE_URL=postgresql://test:test@localhost:5432/austial_test
REDIS_URL=redis://localhost:6379/1
JWT_SECRET=test-secret-key-32-chars-min
API_KEY=test-api-key
DOCUMENTS_S3_BUCKET=austial-test-documents
AWS_REGION=us-east-1
```

### Local Services

```bash
# Start PostgreSQL + Redis + S3 (localstack)
docker compose -f docker-compose.test.yml up -d

# Apply migrations
uv run alembic upgrade head

# Seed test data (if script exists)
uv run python scripts/seed_test_data.py
```

### Frontend Test Setup

```bash
cd frontend/
npm install
npm run build  # ensure no compilation errors
```

---

## Phase 1: Foundation

Phase 1 establishes authentication, guards, migrations, background jobs, and admin infrastructure.

### 1.1 Authentication Module

**Unit Tests:**
```bash
cd backend/
uv run pytest tests/unit/auth_service_spec.py -v
```

**Manual API Tests:**

1. **Register a new user:**
```bash
curl -X POST http://52.6.51.39:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "investor@example.com",
    "password": "SecurePass123!",
    "full_name": "Test Investor"
  }'

# Expected: 201 Created
# Returns: {"id": 1, "email": "...", "role": "INVESTOR", ...}
```

2. **Login:**
```bash
curl -X POST http://52.6.51.39:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "investor@example.com",
    "password": "SecurePass123!"
  }'

# Expected: 200 OK
# Returns: {"access_token": "eyJ...", "refresh_token": "...", "token_type": "bearer"}

# Save the access_token for subsequent requests
export TOKEN="eyJ..."
```

3. **Test JWT auth guard:**
```bash
# Without token (should fail)
curl -X GET http://52.6.51.39:8000/admin/dashboard/summary

# Expected: 401 Unauthorized

# With token (should succeed for ADMIN/COMPLIANCE_OFFICER)
curl -X GET http://52.6.51.39:8000/admin/dashboard/summary \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK (if user is ADMIN/COMPLIANCE_OFFICER)
# Expected: 403 Forbidden (if user is INVESTOR)
```

4. **Refresh token:**
```bash
curl -X POST http://52.6.51.39:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token_from_login>"
  }'

# Expected: 200 OK
# Returns: new token pair
```

5. **Logout:**
```bash
curl -X POST http://52.6.51.39:8000/auth/logout \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token>"
  }'

# Expected: 200 OK
```

### 1.2 Role Guards

**Test role-based access:**

```bash
# Create users with different roles (as ADMIN)
curl -X POST http://52.6.51.39:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "Admin123!", "full_name": "Admin User"}'

# Change role to ADMIN (requires existing ADMIN)
curl -X PATCH http://52.6.51.39:8000/admin/users/1/role \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "ADMIN"}'

# Test ADMIN-only endpoint
curl -X GET http://52.6.51.39:8000/admin/users \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# Expected: 200 OK

curl -X GET http://52.6.51.39:8000/admin/users \
  -H "Authorization: Bearer $INVESTOR_TOKEN"
# Expected: 403 Forbidden
```

### 1.3 KYC Verified Guard

**Unit Test:**
```bash
uv run pytest tests/unit/kyc_verified_guard_spec.py -v
```

**Manual Test:**
```bash
# Try to access investor-only route without KYC verification
curl -X POST http://52.6.51.39:8000/subscriptions \
  -H "Authorization: Bearer $INVESTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}'

# Expected: 403 Forbidden with message "kyc.error.verification_required"
```

### 1.4 Audit Interceptor

**Test audit log creation:**

```bash
# Perform any mutating action
curl -X PATCH http://52.6.51.39:8000/admin/users/1/role \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "COMPLIANCE_OFFICER"}'

# Query audit log (Phase 8 endpoint)
curl -X GET "http://52.6.51.39:8000/compliance/audit-log?entity_type=User&action=ROLE_CHANGED" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Expected: Audit log entry with before_state and after_state
```

### 1.5 Alembic Migrations

```bash
# Check migration status
uv run alembic current

# Test migration rollback/forward
uv run alembic downgrade -1
uv run alembic upgrade head

# Verify all tables exist
psql $DATABASE_URL -c "\dt"
# Expected: user, refresh_token, investor_profile, kyc_submission, etc.
```

### 1.6 Celery Background Jobs

```bash
# Start worker in terminal 1
uv run celery -A src.jobs.celery_app worker --loglevel=info

# Enqueue a test task in terminal 2
python -c "
from src.jobs.tasks import health_check
result = health_check.delay()
print(f'Task ID: {result.id}')
print(f'Result: {result.get(timeout=5)}')
"

# Expected: Task executes, returns "Health check task executed"
```

### 1.7 Object Storage (S3)

**Unit Test:**
```bash
uv run pytest tests/unit/object_storage_service_spec.py -v
```

**Manual Test:**
```bash
# Generate presigned upload URL (Phase 2+ will expose this)
python -c "
from src.storage.object_storage_service import ObjectStorageService
service = ObjectStorageService()
url = service.generate_presigned_upload_url('test/document.pdf', 'application/pdf')
print(url)
"

# Upload a file using the URL (with curl or browser)
curl -X PUT "$PRESIGNED_URL" \
  -H "Content-Type: application/pdf" \
  --data-binary @test-document.pdf

# Generate download URL
python -c "
url = service.generate_presigned_download_url('test/document.pdf')
print(url)
"
# Open URL in browser - should download the file
```

### 1.8 Frontend Auth Flow

```bash
cd frontend/
npm start  # http://austial-demo-frontend-459141725579.s3-website-us-east-1.amazonaws.com

# Manual browser tests:
# 1. Navigate to /login
# 2. Enter credentials → should redirect to /onboarding or /marketplace based on KYC status
# 3. Access /admin without ADMIN role → should redirect to /login or show 403
# 4. Logout → should clear tokens and redirect to /login
```

---

## Phase 2: Identity & KYC

### 2.1 KYC Submission Flow

**API Tests:**

1. **Create investor profile:**
```bash
curl -X POST http://52.6.51.39:8000/investors/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "investor_type": "INDIVIDUAL",
    "jurisdiction": "US",
    "risk_profile": "MODERATE"
  }'
```

2. **Submit KYC documents:**
```bash
# Get presigned upload URL
curl -X POST http://52.6.51.39:8000/kyc/submissions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "PASSPORT"
  }'
# Returns: {"submission_id": 1, "upload_url": "https://..."}

# Upload document to S3 using presigned URL
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: image/jpeg" \
  --data-binary @passport.jpg

# Confirm upload
curl -X PATCH http://52.6.51.39:8000/kyc/submissions/1/confirm-upload \
  -H "Authorization: Bearer $TOKEN"
```

3. **Check KYC status:**
```bash
curl -X GET http://52.6.51.39:8000/kyc/submissions/1 \
  -H "Authorization: Bearer $TOKEN"

# Expected: {"status": "SUBMITTED", ...}
# After auto-screening: "AUTO_SCREENING"
# After compliance review: "VERIFIED" or "REJECTED"
```

### 2.2 Compliance Officer Review Queue

```bash
# Login as compliance officer
curl -X POST http://52.6.51.39:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "officer@example.com", "password": "Officer123!"}'

export OFFICER_TOKEN="..."

# Get pending KYC submissions
curl -X GET "http://52.6.51.39:8000/kyc/submissions?status=MANUAL_REVIEW" \
  -H "Authorization: Bearer $OFFICER_TOKEN"

# Approve submission
curl -X PATCH http://52.6.51.39:8000/kyc/submissions/1/approve \
  -H "Authorization: Bearer $OFFICER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Documents verified, identity confirmed"}'

# Or reject
curl -X PATCH http://52.6.51.39:8000/kyc/submissions/1/reject \
  -H "Authorization: Bearer $OFFICER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Document expired, re-submission required"}'
```

### 2.3 KYC Auto-Screening (Celery Task)

```bash
# Monitor Celery worker logs for OCR extraction task
# Should see: "Starting KYC auto-screening for submission_id=1"

# Check if sanctions screening ran
curl -X GET http://52.6.51.39:8000/kyc/submissions/1/screening-results \
  -H "Authorization: Bearer $OFFICER_TOKEN"

# Expected: {"sanctions_match": false, "liveness_verified": true, ...}
```

---

## Phase 3: Issuers, Custodians, Assets

### 3.1 Issuer Registration

```bash
# Register as issuer
curl -X POST http://52.6.51.39:8000/issuers \
  -H "Authorization: Bearer $ISSUER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Acme Real Estate Fund",
    "jurisdiction": "IN",
    "ifsca_registration_no": "IFSCA/RWA/2026/001",
    "business_type": "FUND_MANAGER"
  }'
```

### 3.2 Custodian Verification

```bash
# Add custodian (ADMIN only)
curl -X POST http://52.6.51.39:8000/custodians \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GIFT City Custodian Services",
    "ifsca_registration_no": "IFSCA/CUST/2025/042",
    "custody_types": ["REAL_ESTATE", "SECURITIES"]
  }'

# Verify custodian IFSCA registration
curl -X PATCH http://52.6.51.39:8000/custodians/1/verify \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"verified": true, "verification_notes": "Confirmed with IFSCA registry"}'
```

### 3.3 Asset Creation

```bash
# Create asset (issuer)
curl -X POST http://52.6.51.39:8000/assets \
  -H "Authorization: Bearer $ISSUER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mumbai Commercial Tower A",
    "asset_class": "REAL_ESTATE",
    "custodian_id": 1,
    "total_value_usd": 5000000.00,
    "description": "Grade-A commercial property in BKC, Mumbai"
  }'

# Verify custodian check (should fail if custodian not IFSCA-verified)
curl -X POST http://52.6.51.39:8000/assets \
  -H "Authorization: Bearer $ISSUER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "custodian_id": 999
  }'
# Expected: 400 Bad Request "Custodian not IFSCA-verified"
```

---

## Phase 4: Issuance Workflow

### 4.1 Tokenization Proposal

```bash
# Create proposal
curl -X POST http://52.6.51.39:8000/issuance/proposals \
  -H "Authorization: Bearer $ISSUER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": 1,
    "total_units": 1000000,
    "unit_price_usd": 5.00,
    "min_subscription_units": 100,
    "subscription_window_start": "2026-09-01T00:00:00Z",
    "subscription_window_end": "2026-09-30T23:59:59Z"
  }'
```

### 4.2 Disclosure Document Upload

```bash
# Upload all 6 required disclosure types
TYPES=("RISK" "FEE" "LIQUIDITY" "CUSTODY" "TAX" "PROSPECTUS")

for TYPE in "${TYPES[@]}"; do
  curl -X POST http://52.6.51.39:8000/issuance/proposals/1/disclosures \
    -H "Authorization: Bearer $ISSUER_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"disclosure_type\": \"$TYPE\",
      \"document_key\": \"proposals/1/disclosures/${TYPE}.pdf\"
    }"
done

# Check completeness
curl -X GET http://52.6.51.39:8000/issuance/proposals/1/disclosures \
  -H "Authorization: Bearer $ISSUER_TOKEN"

# Expected: All 6 types present with status "CURRENT"
```

### 4.3 Issuance State Machine

```bash
# Submit for review (DRAFT → DOCUMENTATION_REVIEW)
curl -X PATCH http://52.6.51.39:8000/issuance/proposals/1/submit \
  -H "Authorization: Bearer $ISSUER_TOKEN"

# Compliance approval (as COMPLIANCE_OFFICER)
curl -X PATCH http://52.6.51.39:8000/issuance/proposals/1/approve \
  -H "Authorization: Bearer $OFFICER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Disclosures complete, risk assessment acceptable"}'

# Status: COMPLIANCE_APPROVED → IFSCA_FILED (manual external process)
# Update status after IFSCA approval
curl -X PATCH http://52.6.51.39:8000/issuance/proposals/1/ifsca-approved \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Launch (creates TokenSeries)
curl -X POST http://52.6.51.39:8000/issuance/proposals/1/launch \
  -H "Authorization: Bearer $OFFICER_TOKEN"

# Expected: 201 Created
# Returns: {"token_series_id": 1, "symbol": "MBCT-A", "supply": 1000000, ...}
```

### 4.4 Disclosure Completeness Gate Test

```bash
# Try to launch with missing disclosure (should fail)
curl -X DELETE http://52.6.51.39:8000/issuance/proposals/1/disclosures/1 \
  -H "Authorization: Bearer $ISSUER_TOKEN"

curl -X POST http://52.6.51.39:8000/issuance/proposals/1/launch \
  -H "Authorization: Bearer $OFFICER_TOKEN"

# Expected: 422 Unprocessable Entity
# Error: "issuance.error.disclosures_incomplete"
```

---

## Phase 5: Ledger & Funding

### 5.1 Ledger Account Creation

```bash
# Account created automatically on investor profile creation
curl -X GET http://52.6.51.39:8000/ledger/accounts/my \
  -H "Authorization: Bearer $INVESTOR_TOKEN"

# Expected: {"available_balance": "0.00", "locked_balance": "0.00", ...}
```

### 5.2 Funding Instruction

```bash
# Request wire transfer instructions
curl -X POST http://52.6.51.39:8000/ledger/funding-instructions \
  -H "Authorization: Bearer $INVESTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_usd": 10000.00
  }'

# Expected: Wire instructions with unique reference code
# Returns: {
#   "beneficiary_bank": "...",
#   "account_number": "...",
#   "reference_code": "FUND-12345-ABCDE",
#   "amount_usd": "10000.00"
# }
```

### 5.3 Bank Webhook (Simulated)

```bash
# Simulate bank webhook confirming wire received
curl -X POST http://52.6.51.39:8000/webhooks/bank/wire-received \
  -H "Content-Type: application/json" \
  -H "X-Bank-Signature: test-signature" \
  -d '{
    "reference_code": "FUND-12345-ABCDE",
    "amount_usd": 10000.00,
    "received_at": "2026-08-22T10:30:00Z",
    "idempotency_key": "unique-tx-id-12345"
  }'

# Check balance updated
curl -X GET http://52.6.51.39:8000/ledger/accounts/my \
  -H "Authorization: Bearer $INVESTOR_TOKEN"

# Expected: {"available_balance": "10000.00", ...}
```

### 5.4 Idempotency Test

```bash
# Send same webhook twice (should not double-credit)
curl -X POST http://52.6.51.39:8000/webhooks/bank/wire-received \
  -H "Content-Type: application/json" \
  -d '{
    "reference_code": "FUND-12345-ABCDE",
    "idempotency_key": "unique-tx-id-12345"
  }'

# Check balance unchanged
curl -X GET http://52.6.51.39:8000/ledger/accounts/my \
  -H "Authorization: Bearer $INVESTOR_TOKEN"

# Expected: {"available_balance": "10000.00", ...} (not 20000.00)
```

### 5.5 Ledger Entry Append-Only Test

```bash
# Unit test (Python)
uv run pytest tests/unit/ledger_service_spec.py::test_ledger_entry_immutable -v

# Expected: Attempting to update/delete LedgerEntry raises exception
```

---

## Phase 6: Subscription & Allocation (MVP)

### 6.1 Subscription Flow

```bash
# Browse marketplace
curl -X GET http://52.6.51.39:8000/assets?status=LAUNCHED \
  -H "Authorization: Bearer $INVESTOR_TOKEN"

# Subscribe to token series
curl -X POST http://52.6.51.39:8000/subscriptions \
  -H "Authorization: Bearer $INVESTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token_series_id": 1,
    "quantity": 500,
    "acknowledged_risk": true,
    "acknowledged_fees": true
  }'

# Expected: {"subscription_id": 1, "status": "PENDING", "locked_amount": "2500.00"}

# Check locked balance
curl -X GET http://52.6.51.39:8000/ledger/accounts/my \
  -H "Authorization: Bearer $INVESTOR_TOKEN"

# Expected: {"available_balance": "7500.00", "locked_balance": "2500.00"}
```

### 6.2 Allocation Engine

```bash
# Close subscription window (as COMPLIANCE_OFFICER)
curl -X POST http://52.6.51.39:8000/issuance/token-series/1/close-subscription \
  -H "Authorization: Bearer $OFFICER_TOKEN"

# Run allocation (background job)
# Monitor Celery logs: "Running allocation for token_series_id=1"

# Check allocation result
curl -X GET http://52.6.51.39:8000/subscriptions/1 \
  -H "Authorization: Bearer $INVESTOR_TOKEN"

# Expected: {"status": "ALLOCATED", "allocated_quantity": 500, ...}
```

### 6.3 Token Holding Creation

```bash
# Check holdings after custodian confirmation
curl -X GET http://52.6.51.39:8000/holdings/my \
  -H "Authorization: Bearer $INVESTOR_TOKEN"

# Expected: [
#   {
#     "token_series_id": 1,
#     "quantity": "500.00000000",
#     "avg_cost_usd": "5.00",
#     "status": "ACTIVE"
#   }
# ]
```

### 6.4 KYC Verification Guard Test

```bash
# Try to subscribe without KYC (should fail)
curl -X POST http://52.6.51.39:8000/subscriptions \
  -H "Authorization: Bearer $UNVERIFIED_INVESTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}'

# Expected: 403 Forbidden "kyc.error.verification_required"
```

---

## Phase 7: Valuation, Redemption, Distribution

### 7.1 Valuation Feed

```bash
# Post NAV update (as issuer or valuation oracle)
curl -X POST http://52.6.51.39:8000/valuation/feeds \
  -H "Authorization: Bearer $ISSUER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token_series_id": 1,
    "nav_per_unit": 5.25,
    "effective_date": "2026-08-22",
    "source": "Independent Valuer XYZ"
  }'

# Expected: {"feed_id": 1, "status": "PUBLISHED"}
```

### 7.2 Anomaly Detection Test

```bash
# Post outlier NAV (should be quarantined)
curl -X POST http://52.6.51.39:8000/valuation/feeds \
  -H "Authorization: Bearer $ISSUER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token_series_id": 1,
    "nav_per_unit": 50.00
  }'

# Expected: {"feed_id": 2, "status": "QUARANTINED", "anomaly_score": 0.95}

# Admin review quarantined feed
curl -X GET "http://52.6.51.39:8000/admin/valuation-oracle?status=QUARANTINED" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Manually approve/reject
curl -X PATCH http://52.6.51.39:8000/valuation/feeds/2/approve \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 7.3 Redemption Request

```bash
# Request redemption
curl -X POST http://52.6.51.39:8000/redemptions/requests \
  -H "Authorization: Bearer $INVESTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "holding_id": 1,
    "quantity": 100
  }'

# Expected: {"request_id": 1, "status": "PENDING_APPROVAL"}

# Compliance officer approval
curl -X PATCH http://52.6.51.39:8000/redemptions/requests/1/approve \
  -H "Authorization: Bearer $OFFICER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Liquidity terms met, approved"}'

# Expected: Status → APPROVED → PROCESSING → COMPLETED
# Check payout instruction created
curl -X GET http://52.6.51.39:8000/ledger/payout-instructions?redemption_request_id=1 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 7.4 Distribution

```bash
# Create distribution (as issuer)
curl -X POST http://52.6.51.39:8000/distributions \
  -H "Authorization: Bearer $ISSUER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token_series_id": 1,
    "distribution_type": "DIVIDEND",
    "amount_per_unit": 0.10,
    "record_date": "2026-08-22",
    "payment_date": "2026-08-30"
  }'

# Background job calculates pro-rata distributions
# Check distribution received
curl -X GET http://52.6.51.39:8000/distributions/my \
  -H "Authorization: Bearer $INVESTOR_TOKEN"

# Expected: [{"amount_usd": "50.00", "status": "PAID", ...}]
```

---

## Phase 8: Compliance & Reporting

### 8.1 AML Alert Creation

```bash
# Alerts auto-generated on suspicious transactions
# Simulate large transaction triggering alert
curl -X POST http://52.6.51.39:8000/ledger/funding-instructions \
  -H "Authorization: Bearer $INVESTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_usd": 150000.00
  }'

# Check AML alert created
curl -X GET "http://52.6.51.39:8000/compliance/aml-alerts?status=OPEN" \
  -H "Authorization: Bearer $OFFICER_TOKEN"

# Expected: [
#   {
#     "alert_id": 1,
#     "alert_type": "LARGE_TRANSACTION",
#     "risk_score": 75.50,
#     "status": "OPEN"
#   }
# ]
```

### 8.2 AML Alert Resolution

```bash
# Assign alert to self
curl -X PATCH http://52.6.51.39:8000/compliance/aml-alerts/1/assign \
  -H "Authorization: Bearer $OFFICER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "officer_id": 2
  }'

# Resolve alert
curl -X PATCH http://52.6.51.39:8000/compliance/aml-alerts/1/resolve \
  -H "Authorization: Bearer $OFFICER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "DISMISSED",
    "notes": "Source of funds verified, legitimate business income"
  }'

# Verify audit log entry created
curl -X GET "http://52.6.51.39:8000/compliance/audit-log?entity_type=AmlAlert&entity_id=1" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Expected: Audit entry with before_state (OPEN) and after_state (DISMISSED)
```

### 8.3 Compliance Report Generation

```bash
# Generate quarterly IFSCA report
curl -X POST http://52.6.51.39:8000/compliance/reports/generate \
  -H "Authorization: Bearer $OFFICER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "QUARTERLY_IFSCA",
    "period_start": "2026-07-01",
    "period_end": "2026-09-30"
  }'

# Expected: {"report_id": 1, "status": "DRAFT"}

# Background job generates PDF (monitor Celery logs)
# "Generating compliance report PDF for report_id=1"

# Check report status
curl -X GET http://52.6.51.39:8000/compliance/reports/1 \
  -H "Authorization: Bearer $OFFICER_TOKEN"

# Expected: {"status": "FINALIZED", "file_storage_key": "reports/2026-Q3.pdf"}

# Download report
curl -X GET http://52.6.51.39:8000/compliance/reports/1/download \
  -H "Authorization: Bearer $OFFICER_TOKEN"

# Expected: {"url": "https://s3.../reports/2026-Q3.pdf?X-Amz-..."}
```

### 8.4 Aggregation Query Tests

```bash
# Unit tests for ORM aggregation
uv run pytest tests/unit/compliance_service_spec.py::test_quarterly_report_aggregation -v

# Expected: Validates sum()/count()/group_by() used correctly
# AUM = sum(quantity * avg_cost_usd) from TokenHolding
# Investor count = count(distinct investor_id) where kyc_status=VERIFIED
# Currency breakdown = sum(amount) group by currency from LedgerEntry
```

### 8.5 Audit Log Viewer (Frontend)

```bash
cd frontend/
npm start

# Browser:
# 1. Login as ADMIN or COMPLIANCE_OFFICER
# 2. Navigate to /admin/audit-log
# 3. Apply filters: date range, entity type (User, AmlAlert, TokenHolding)
# 4. Click "View details" on any entry
# 5. Verify before/after state JSON diff displayed correctly
```

---

## Phase 9: AI/ML Layer

### 9.1 KYC OCR Service

```bash
# Unit test
uv run pytest tests/unit/ml_services_spec.py::test_kyc_ocr_extraction -v

# Integration test (requires tesseract binary)
python -c "
from src.modules.ml.services.kyc_ml_service import KycMlService
service = KycMlService()

with open('test-passport.jpg', 'rb') as f:
    result = service.extract_kyc_fields(f.read(), 'PASSPORT')
    print(result)
"

# Expected: {
#   "name": "JOHN DOE",
#   "passport_number": "P12345678",
#   "date_of_birth": "1985-03-15",
#   ...
# }
```

### 9.2 Face Matching

```bash
python -c "
from src.modules.ml.services.kyc_ml_service import KycMlService
service = KycMlService()

with open('selfie.jpg', 'rb') as f1, open('passport-photo.jpg', 'rb') as f2:
    result = service.match_face(f1.read(), f2.read())
    print(result)
"

# Expected: {"match": true, "similarity_score": 0.87, "confidence": 0.92}
```

### 9.3 AML Transaction Scoring

```bash
# Unit test
uv run pytest tests/unit/ml_services_spec.py::test_aml_scoring -v

# Integration test
python -c "
from src.modules.ml.services.aml_scoring_service import AmlScoringService
service = AmlScoringService()

transaction_data = {
    'amount_usd': 95000.0,
    'hour_of_day': 23,
    'days_since_last_tx': 0,
    'jurisdiction_risk_tier': 3,
    'past_alert_count': 2
}

result = service.score_transaction(transaction_data)
print(result)
"

# Expected: {
#   "risk_score": 82.5,
#   "risk_level": "HIGH",
#   "model_version": "xgb_v1"
# }
```

### 9.4 Valuation Anomaly Detection

```bash
python -c "
from src.modules.ml.services.valuation_anomaly_service import ValuationAnomalyService
service = ValuationAnomalyService()

trailing_prices = [5.10, 5.15, 5.08, 5.12, 5.14]
new_price = 15.50

result = service.detect_anomaly(1, new_price, trailing_prices)
print(result)
"

# Expected: {
#   "anomaly_score": 0.98,
#   "is_anomaly": true,
#   "z_score": 8.45,
#   "recommendation": "QUARANTINE"
# }
```

### 9.5 ML Prediction Audit Trail

```bash
# Check all ML predictions logged
curl -X GET "http://52.6.51.39:8000/ml/predictions?model_name=aml_scoring&limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Expected: [
#   {
#     "model_name": "aml_scoring",
#     "model_version": "xgb_v1",
#     "input_features": {"amount_usd": 95000, ...},
#     "prediction_output": {"risk_score": 82.5, ...},
#     "entity_type": "LedgerEntry",
#     "entity_id": 123,
#     "predicted_at": "2026-08-22T12:34:56Z"
#   }
# ]
```

### 9.6 Train XGBoost Model

```bash
# Run training script
cd backend/
uv run python src/modules/ml/scripts/train_aml_model.py

# Expected output:
# "Training AML scoring model..."
# "Model saved to models/aml_xgboost_v1.pkl"
# "Accuracy: 0.87"

# Verify model file exists
ls -lh models/aml_xgboost_v1.pkl

# Test model loads correctly
python -c "
import joblib
model = joblib.load('models/aml_xgboost_v1.pkl')
print(f'Model type: {type(model)}')
print(f'Features: {model.feature_names_in_}')
"
```

---

## Integration Testing

### End-to-End User Journey

```bash
#!/bin/bash
# Full investor journey test script

# 1. Register
TOKEN=$(curl -X POST http://52.6.51.39:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test123!", "full_name": "Test User"}' \
  | jq -r '.access_token')

# 2. Create investor profile
curl -X POST http://52.6.51.39:8000/investors/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"investor_type": "INDIVIDUAL", "jurisdiction": "US"}'

# 3. Submit KYC
SUBMISSION_ID=$(curl -X POST http://52.6.51.39:8000/kyc/submissions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_type": "PASSPORT"}' \
  | jq -r '.submission_id')

# 4. Upload document (mock)
# ... upload to S3 using presigned URL ...

# 5. Fund account (simulate wire)
curl -X POST http://52.6.51.39:8000/webhooks/bank/wire-received \
  -H "Content-Type: application/json" \
  -d "{\"reference_code\": \"FUND-$SUBMISSION_ID\", \"amount_usd\": 10000}"

# 6. Subscribe to asset
curl -X POST http://52.6.51.39:8000/subscriptions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"token_series_id": 1, "quantity": 500}'

# 7. Check holding
curl -X GET http://52.6.51.39:8000/holdings/my \
  -H "Authorization: Bearer $TOKEN"

# Expected: Full journey completes without errors
```

### Cross-Module Integration Tests

```bash
# Test KYC → ML integration
uv run pytest tests/integration/test_kyc_ml_integration.py -v

# Test Subscription → Ledger integration
uv run pytest tests/integration/test_subscription_ledger_integration.py -v

# Test Compliance → AML ML integration
uv run pytest tests/integration/test_compliance_aml_ml_integration.py -v
```

---

## Performance Testing

### Load Testing with Locust

```bash
# Install locust
pip install locust

# Run load test
cd backend/tests/load/
locust -f locustfile.py --host=http://52.6.51.39:8000

# Open browser: http://localhost:8089
# Start swarming: 100 users, spawn rate 10/sec
```

**Sample locustfile.py:**
```python
from locust import HttpUser, task, between

class AustialUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login
        response = self.client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "Test123!"
        })
        self.token = response.json()["access_token"]
    
    @task(3)
    def get_holdings(self):
        self.client.get("/holdings/my", headers={
            "Authorization": f"Bearer {self.token}"
        })
    
    @task(1)
    def get_marketplace(self):
        self.client.get("/assets?status=LAUNCHED", headers={
            "Authorization": f"Bearer {self.token}"
        })
```

### Database Query Performance

```bash
# Check slow queries
psql $DATABASE_URL -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# Test aggregation query performance (Phase 8)
time curl -X POST http://52.6.51.39:8000/compliance/reports/generate \
  -H "Authorization: Bearer $OFFICER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"report_type": "QUARTERLY_IFSCA", "period_start": "2026-07-01", "period_end": "2026-09-30"}'

# Expected: < 2 seconds for 10k holdings, 1k investors
```

---

## Security Testing

### Authentication Tests

```bash
# Test JWT expiration
TOKEN="expired.jwt.token"
curl -X GET http://52.6.51.39:8000/holdings/my \
  -H "Authorization: Bearer $TOKEN"
# Expected: 401 Unauthorized

# Test password hashing (bcrypt)
uv run pytest tests/unit/auth_service_spec.py::test_password_not_stored_plaintext -v
```

### Authorization Tests

```bash
# Test role escalation prevention
curl -X PATCH http://52.6.51.39:8000/admin/users/1/role \
  -H "Authorization: Bearer $INVESTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "ADMIN"}'
# Expected: 403 Forbidden

# Test KYC bypass prevention
curl -X POST http://52.6.51.39:8000/subscriptions \
  -H "Authorization: Bearer $UNVERIFIED_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}'
# Expected: 403 Forbidden
```

### SQL Injection Tests

```bash
# Test parameterized queries (should not be vulnerable)
curl -X GET "http://52.6.51.39:8000/assets?search=' OR '1'='1" \
  -H "Authorization: Bearer $TOKEN"

# Expected: Empty results or safe handling, no SQL error
```

### CORS Tests

```bash
# Test CORS headers
curl -X OPTIONS http://52.6.51.39:8000/auth/login \
  -H "Origin: http://malicious-site.com" \
  -H "Access-Control-Request-Method: POST"

# Expected: CORS rejection or whitelisted origin only
```

---

## Frontend Testing

### Unit Tests

```bash
cd frontend/
npm test

# Run specific suite
npm test -- --include=**/compliance/**/*.spec.ts

# Coverage
npm test -- --code-coverage
```

### E2E Tests (Playwright/Cypress)

```bash
# Install e2e framework
npm install -D @playwright/test

# Run e2e tests
npm run e2e

# Headed mode (watch browser)
npm run e2e -- --headed
```

**Sample e2e test:**
```typescript
// e2e/admin/aml-queue.spec.ts
import { test, expect } from '@playwright/test';

test('compliance officer can resolve AML alert', async ({ page }) => {
  // Login
  await page.goto('http://austial-demo-frontend-459141725579.s3-website-us-east-1.amazonaws.com/login');
  await page.fill('input[name="email"]', 'officer@example.com');
  await page.fill('input[name="password"]', 'Officer123!');
  await page.click('button[type="submit"]');
  
  // Navigate to AML queue
  await page.goto('http://austial-demo-frontend-459141725579.s3-website-us-east-1.amazonaws.com/admin/compliance');
  
  // Find first alert
  await page.click('table tbody tr:first-child button:has-text("Resolve")');
  
  // Fill resolution dialog
  await page.check('input[value="DISMISSED"]');
  await page.fill('textarea[name="notes"]', 'Verified source of funds');
  await page.click('button:has-text("Confirm")');
  
  // Verify success
  await expect(page.locator('.alert-success')).toBeVisible();
});
```

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
      redis:
        image: redis:7
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v1
      
      - name: Install dependencies
        run: |
          cd backend
          uv sync
      
      - name: Run migrations
        run: |
          cd backend
          uv run alembic upgrade head
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/test
      
      - name: Run tests
        run: |
          cd backend
          uv run pytest --cov=src --cov-report=xml
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379/0
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 20
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run tests
        run: |
          cd frontend
          npm test -- --watch=false --code-coverage
      
      - name: Build
        run: |
          cd frontend
          npm run build
```

---

## Troubleshooting

### Common Issues

**1. "Module not found: austial.orm"**
```bash
# Ensure using uv run, not global austial
cd backend/
uv run python -c "import austial.orm; print(austial.orm.__file__)"
```

**2. Database connection fails**
```bash
# Check PostgreSQL running
docker ps | grep postgres

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

**3. Celery tasks not executing**
```bash
# Check Redis connection
redis-cli ping

# Check worker running
ps aux | grep celery

# Check broker connection
python -c "from src.jobs.celery_app import celery_app; print(celery_app.broker_url)"
```

**4. S3 upload fails**
```bash
# Check AWS credentials
aws s3 ls s3://$DOCUMENTS_S3_BUCKET/ --profile default

# Test presigned URL generation
python -c "
from src.storage.object_storage_service import ObjectStorageService
svc = ObjectStorageService()
print(svc.generate_presigned_upload_url('test.pdf', 'application/pdf'))
"
```

**5. ML model predictions fail**
```bash
# Check tesseract installed
which tesseract
tesseract --version

# Check opencv installed
python -c "import cv2; print(cv2.__version__)"

# Check model file exists
ls -lh backend/models/aml_xgboost_v1.pkl
```

---

## Test Coverage Goals

| Module | Unit Test Coverage | Integration Test Coverage |
|---|---|---|
| Auth | > 90% | > 80% |
| KYC | > 85% | > 75% |
| Issuance | > 90% | > 80% |
| Ledger | > 95% (append-only critical) | > 85% |
| Compliance | > 90% | > 80% |
| ML | > 80% | > 70% |

Run coverage report:
```bash
cd backend/
uv run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

---

**Last Updated:** 2026-08-22 (Phase 8 & 9 complete)
