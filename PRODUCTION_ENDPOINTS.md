# Production Endpoints Quick Reference

## 🌐 Base URLs

| Service | URL | Status |
|---------|-----|--------|
| **Backend API** | `http://52.6.51.39:8000` | ✅ Live |
| **Frontend** | `http://austial-demo-frontend-459141725579.s3-website-us-east-1.amazonaws.com` | ✅ Live |
| **Swagger Docs** | `http://52.6.51.39:8000/docs` | ✅ Available |

**AWS Deployment:**
- Region: `us-east-1`
- Account: `459141725579`
- Profile: `aayush-gift`

---

## 🔑 Authentication Endpoints

```bash
# Register
curl -X POST http://52.6.51.39:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "Pass123!", "full_name": "User Name"}'

# Login
curl -X POST http://52.6.51.39:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "Pass123!"}'
# Returns: {"access_token": "...", "refresh_token": "..."}

# Refresh
curl -X POST http://52.6.51.39:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "..."}'

# Logout
curl -X POST http://52.6.51.39:8000/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "..."}'
```

---

## 🏥 Health & Status

```bash
# Public health check
curl http://52.6.51.39:8000/health

# Protected health check (requires API key)
curl http://52.6.51.39:8000/health/protected \
  -H "x-api-key: YOUR_API_KEY"
```

---

## 👤 Phase 2: KYC & Investors

```bash
# Create investor profile
curl -X POST http://52.6.51.39:8000/investors/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"investor_type": "INDIVIDUAL", "jurisdiction": "US", "risk_profile": "MODERATE"}'

# Submit KYC
curl -X POST http://52.6.51.39:8000/kyc/submissions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_type": "PASSPORT"}'

# Check KYC status
curl -X GET http://52.6.51.39:8000/kyc/submissions/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🏢 Phase 3: Issuers, Custodians, Assets

```bash
# List assets
curl -X GET http://52.6.51.39:8000/assets?status=LAUNCHED \
  -H "Authorization: Bearer $TOKEN"

# Get asset details
curl -X GET http://52.6.51.39:8000/assets/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🚀 Phase 4: Issuance

```bash
# List token series
curl -X GET http://52.6.51.39:8000/issuance/token-series \
  -H "Authorization: Bearer $TOKEN"

# Get issuance proposal
curl -X GET http://52.6.51.39:8000/issuance/proposals/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## 💰 Phase 5: Ledger & Funding

```bash
# Get my ledger account
curl -X GET http://52.6.51.39:8000/ledger/accounts/my \
  -H "Authorization: Bearer $TOKEN"

# Request funding instructions
curl -X POST http://52.6.51.39:8000/ledger/funding-instructions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount_usd": 10000.00}'
```

---

## 📊 Phase 6: Subscriptions & Holdings

```bash
# Subscribe to token
curl -X POST http://52.6.51.39:8000/subscriptions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"token_series_id": 1, "quantity": 500, "acknowledged_risk": true, "acknowledged_fees": true}'

# Get my holdings
curl -X GET http://52.6.51.39:8000/holdings/my \
  -H "Authorization: Bearer $TOKEN"

# Get holding details
curl -X GET http://52.6.51.39:8000/holdings/1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📈 Phase 7: Valuation & Redemptions

```bash
# Get latest valuation
curl -X GET http://52.6.51.39:8000/valuation/feeds?token_series_id=1 \
  -H "Authorization: Bearer $TOKEN"

# Request redemption
curl -X POST http://52.6.51.39:8000/redemptions/requests \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"holding_id": 1, "quantity": 100}'

# Get my distributions
curl -X GET http://52.6.51.39:8000/distributions/my \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🛡️ Phase 8: Compliance & Reporting

```bash
# Get AML alerts (COMPLIANCE_OFFICER/ADMIN)
curl -X GET "http://52.6.51.39:8000/compliance/aml-alerts?status=OPEN" \
  -H "Authorization: Bearer $OFFICER_TOKEN"

# Resolve AML alert
curl -X PATCH http://52.6.51.39:8000/compliance/aml-alerts/1/resolve \
  -H "Authorization: Bearer $OFFICER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "DISMISSED", "notes": "Verified source of funds"}'

# Generate compliance report
curl -X POST http://52.6.51.39:8000/compliance/reports/generate \
  -H "Authorization: Bearer $OFFICER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"report_type": "QUARTERLY_IFSCA", "period_start": "2026-07-01", "period_end": "2026-09-30"}'

# Get compliance reports
curl -X GET http://52.6.51.39:8000/compliance/reports \
  -H "Authorization: Bearer $OFFICER_TOKEN"

# Get audit log
curl -X GET "http://52.6.51.39:8000/compliance/audit-log?entity_type=User" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## 🤖 Phase 9: ML & AI

```bash
# Get ML models (ADMIN)
curl -X GET http://52.6.51.39:8000/ml/models \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Get ML predictions
curl -X GET "http://52.6.51.39:8000/ml/predictions?model_name=aml_scoring&limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## 👨‍💼 Admin Endpoints

```bash
# Dashboard summary
curl -X GET http://52.6.51.39:8000/admin/dashboard/summary \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# List users
curl -X GET "http://52.6.51.39:8000/admin/users?search=test&skip=0&take=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Change user role
curl -X PATCH http://52.6.51.39:8000/admin/users/1/role \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "COMPLIANCE_OFFICER"}'

# Suspend user
curl -X PATCH http://52.6.51.39:8000/admin/users/1/suspend \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"suspended": true}'
```

---

## 🔒 Role Requirements

| Role | Endpoints |
|------|-----------|
| **PUBLIC** | `/auth/*`, `/health`, `/docs` |
| **INVESTOR** | `/investors/*`, `/holdings/*`, `/subscriptions/*`, `/ledger/accounts/my`, `/distributions/my` |
| **ISSUER** | `/issuers/*`, `/assets/*`, `/issuance/*` |
| **COMPLIANCE_OFFICER** | `/kyc/submissions/*/approve`, `/compliance/*`, `/admin/dashboard/summary`, `/admin/audit-log` |
| **ADMIN** | `/admin/*`, All other endpoints |

**KYC Verification Required:**
- All subscription, holding, and redemption endpoints require `kyc_status = VERIFIED`
- Enforced by `KycVerifiedGuard`

---

## 🧪 Testing Commands

```bash
# Quick health check
curl http://52.6.51.39:8000/health

# Get API documentation
open http://52.6.51.39:8000/docs

# Test frontend
open http://austial-demo-frontend-459141725579.s3-website-us-east-1.amazonaws.com

# Run Phase 8/9 endpoint tests
cd austial-hackathon/
API_URL=http://52.6.51.39:8000 ./scripts/test-phase8-9.sh
```

---

## 📚 Full Testing Guide

For comprehensive phase-by-phase testing instructions, see **[`TESTING.md`](TESTING.md)**.

---

**Last Updated:** 2026-08-22 (All 9 phases deployed)
