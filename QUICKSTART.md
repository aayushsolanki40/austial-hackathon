# Austial/Swadely Quick Start Guide

Get started testing the live production deployment in minutes.

## 🚀 Production is Live!

**Backend:** http://52.6.51.39:8000  
**Frontend:** http://austial-demo-frontend-459141725579.s3-website-us-east-1.amazonaws.com  
**API Docs:** http://52.6.51.39:8000/docs

All 9 phases deployed and operational. ✅

---

## 1️⃣ Test the API (30 seconds)

```bash
# Health check
curl http://52.6.51.39:8000/health

# Expected: {"status": "ok", "info": {...}}
```

---

## 2️⃣ Create an Account (2 minutes)

```bash
# Register
curl -X POST http://52.6.51.39:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your.email@example.com",
    "password": "SecurePass123!",
    "full_name": "Your Name"
  }'

# Login
curl -X POST http://52.6.51.39:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your.email@example.com",
    "password": "SecurePass123!"
  }'

# Save the access_token from the response
export TOKEN="<paste_access_token_here>"
```

---

## 3️⃣ Try an Authenticated Endpoint (1 minute)

```bash
# Create investor profile
curl -X POST http://52.6.51.39:8000/investors/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "investor_type": "INDIVIDUAL",
    "jurisdiction": "US",
    "risk_profile": "MODERATE"
  }'

# Expected: {"id": 1, "investor_type": "INDIVIDUAL", ...}
```

---

## 4️⃣ Explore the Frontend (2 minutes)

Open in browser:
```
http://austial-demo-frontend-459141725579.s3-website-us-east-1.amazonaws.com
```

1. Click "Login"
2. Enter credentials from step 2
3. Navigate to:
   - **Marketplace** → Browse tokenized assets
   - **Portfolio** → View holdings
   - **Wallet** → Check balance
   - **Admin** (if role = ADMIN/COMPLIANCE_OFFICER) → AML alerts, reports, audit log

---

## 5️⃣ Test Phase 8 & 9 Features (3 minutes)

```bash
# Clone repo
git clone https://github.com/aayushsolanki40/austial-hackathon.git
cd austial-hackathon/

# Run automated tests against production
./scripts/test-phase8-9.sh
```

Tests:
- ✅ AML alert service (Phase 8)
- ✅ Compliance report generation (Phase 8)
- ✅ Audit log (Phase 8)
- ✅ KYC ML (OCR, liveness, face matching) (Phase 9)
- ✅ AML scoring (XGBoost) (Phase 9)
- ✅ Valuation anomaly detection (Phase 9)

---

## 📚 Full Documentation

| Document | Purpose |
|----------|---------|
| **[PRODUCTION_ENDPOINTS.md](PRODUCTION_ENDPOINTS.md)** | Complete API reference with curl examples |
| **[TESTING.md](TESTING.md)** | Comprehensive phase-by-phase testing guide (13,500+ lines) |
| **[backend/README.md](backend/README.md)** | Backend setup, architecture, development |
| **[frontend/README.md](frontend/README.md)** | Frontend setup, architecture, components |
| **[AUSTIAL_BUILD_PLAN.md](AUSTIAL_BUILD_PLAN.md)** | Original 9-phase build plan with domain model |

---

## 🔑 Roles & Access

New accounts are created as **INVESTOR** by default.

| Role | Can Access |
|------|------------|
| **INVESTOR** | Marketplace, portfolio, wallet, subscriptions, redemptions |
| **ISSUER** | Asset creation, issuance proposals, disclosures |
| **COMPLIANCE_OFFICER** | KYC review, AML alerts, compliance reports, audit log |
| **ADMIN** | Everything + user management, role changes |

**To test admin features:**
1. Create account
2. Contact admin to change your role
3. OR use the seed data (if seeded) with pre-configured admin accounts

---

## 🧪 Run Automated Tests

```bash
# Full test suite (backend + frontend)
./scripts/test-quick.sh

# Phase 8 & 9 only
./scripts/test-phase8-9.sh

# Backend unit tests
cd backend/
uv run pytest

# Frontend tests
cd frontend/
npm test
```

---

## 🛠️ Common Tasks

### View Swagger API Docs
```
http://52.6.51.39:8000/docs
```

### Test KYC Submission Flow
```bash
# 1. Create investor profile (from step 3)
# 2. Submit KYC
curl -X POST http://52.6.51.39:8000/kyc/submissions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_type": "PASSPORT"}'

# 3. Check status
curl -X GET http://52.6.51.39:8000/kyc/submissions/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Test AML Alerts (Compliance Officer)
```bash
# Login as compliance officer
# (Need COMPLIANCE_OFFICER role)

curl -X GET "http://52.6.51.39:8000/compliance/aml-alerts?status=OPEN" \
  -H "Authorization: Bearer $OFFICER_TOKEN"
```

### Generate Compliance Report (Compliance Officer)
```bash
curl -X POST http://52.6.51.39:8000/compliance/reports/generate \
  -H "Authorization: Bearer $OFFICER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "QUARTERLY_IFSCA",
    "period_start": "2026-07-01",
    "period_end": "2026-09-30"
  }'
```

---

## 🏗️ Architecture Overview

```
austial-hackathon/
├── backend/          # Python + Austial framework
│   ├── src/
│   │   └── modules/  # 17 domain modules (auth, kyc, compliance, ml, ...)
│   ├── tests/        # Unit + integration tests
│   └── alembic/      # Database migrations
├── frontend/         # Angular 19 + Material
│   ├── src/app/
│   │   └── features/ # Admin, marketplace, portfolio, wallet, KYC
│   └── tests/        # Unit + e2e tests
├── infra/terraform/  # AWS deployment (EC2, RDS, S3, ECR)
└── scripts/          # Automated test scripts
```

**Tech Stack:**
- Backend: Python 3.11+, Austial (FastAPI-based), PostgreSQL, Redis, Celery
- Frontend: Angular 19, Material, TypeScript
- ML: scikit-learn, XGBoost, Tesseract OCR, OpenCV
- Deployment: AWS (EC2, RDS, S3, ECR), Terraform

---

## 💡 What's Built

### Phase 1-7 (MVP Complete)
✅ Auth & role-based guards  
✅ KYC submission & compliance review  
✅ Issuer/custodian/asset management  
✅ Tokenization issuance workflow (6-disclosure completeness gate)  
✅ Ledger, funding, subscriptions  
✅ Allocation engine, holdings (investor-keyed)  
✅ Valuation feeds, redemptions, distributions  

### Phase 8 (Compliance & Reporting)
✅ AML alert creation & resolution  
✅ Quarterly IFSCA compliance report generator  
✅ Immutable audit log viewer  
✅ 7-year retention enforcement  
✅ ORM aggregation queries (sum/count/group_by)  

### Phase 9 (AI/ML Layer)
✅ KYC OCR (Tesseract), liveness, face matching (OpenCV)  
✅ AML transaction scoring (XGBoost)  
✅ Valuation anomaly detection (z-score + IQR)  
✅ Smart contract risk scoring  
✅ ML prediction audit trail (regulatory compliance)  

---

## 🆘 Troubleshooting

**Can't connect to API:**
```bash
# Verify API is up
curl http://52.6.51.39:8000/health

# Check EC2 instance status
aws ec2 describe-instances --instance-ids i-030ade8f2639274ae \
  --profile aayush-gift --region us-east-1
```

**401 Unauthorized:**
- Check token is valid (not expired)
- Verify `Authorization: Bearer <token>` header format
- Re-login to get fresh token

**403 Forbidden:**
- Check your role (e.g. `/admin/*` requires ADMIN role)
- KYC-related endpoints require `kyc_status = VERIFIED`

**Need help?**
- See [TESTING.md](TESTING.md) for detailed troubleshooting
- Check [PRODUCTION_ENDPOINTS.md](PRODUCTION_ENDPOINTS.md) for correct endpoint URLs
- Review backend logs on EC2

---

## 🎯 Next Steps

1. **Explore the API:** Try different endpoints from [PRODUCTION_ENDPOINTS.md](PRODUCTION_ENDPOINTS.md)
2. **Complete KYC flow:** Submit → auto-screening → compliance review → verification
3. **Test tokenization:** Create asset → proposal → disclosures → launch → subscribe
4. **Review compliance:** AML alerts → resolution → report generation
5. **Test ML features:** OCR extraction, AML scoring, anomaly detection

---

**Platform Status:** ✅ All 9 phases complete | 🚀 Production live | 📊 24 entities | 🔐 IFSCA-compliant

**Last Updated:** 2026-08-22
