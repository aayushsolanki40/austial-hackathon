# Backend Scripts

Utility scripts for database seeding, maintenance, and operations.

## seed_demo_data.py

Creates comprehensive demo data for all user roles in the Swadely platform.

### What It Creates

- **7 demo users** across all roles:
  - 3 INVESTOR users (APPROVED, PENDING, REJECTED KYC)
  - 2 ISSUER users (VERIFIED, PENDING)
  - 1 COMPLIANCE_OFFICER
  - 1 ADMIN

- **Complete domain data**:
  - Investor profiles with KYC submissions, risk consents, wallet mappings
  - Issuer profiles with verification statuses
  - 3 custodians (2 verified, 1 pending)
  - 4 assets across different asset classes
  - 4 tokenization proposals in various states
  - 2 launched token series (MBO-2024, GIB-A24)
  - Ledger accounts with USD balances
  - Subscriptions and holdings showing ownership
  - NAV feeds showing valuation history
  - Redemption requests in different states
  - AML alerts for compliance review
  - Audit logs showing system activity

### Demo Credentials

All demo accounts use the same password: **Demo123!**

| Email | Role | Notes |
|-------|------|-------|
| investor1@demo.swadely.com | INVESTOR | APPROVED KYC, has holdings |
| investor2@demo.swadely.com | INVESTOR | PENDING KYC |
| investor3@demo.swadely.com | INVESTOR | REJECTED KYC |
| issuer1@demo.swadely.com | ISSUER | VERIFIED, has launched assets |
| issuer2@demo.swadely.com | ISSUER | PENDING verification |
| compliance@demo.swadely.com | COMPLIANCE_OFFICER | Can review KYC/AML/redemptions |
| admin@demo.swadely.com | ADMIN | Full system access |

### Usage

#### Local Database

```bash
cd backend
uv run python scripts/seed_demo_data.py
```

#### Production Database

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db" uv run python scripts/seed_demo_data.py
```

Or use the production env:

```bash
cd backend
# Export production DATABASE_URL from .env or manually
export DATABASE_URL="<production-url>"
uv run python scripts/seed_demo_data.py
```

### Features

- **Idempotent**: Can be run multiple times. Prompts before deleting existing demo data.
- **Comprehensive**: Creates data across all modules to demonstrate complete workflows.
- **Realistic**: Uses proper financial amounts, realistic names, proper state transitions.
- **Safe**: Only affects records with `@demo.swadely.com` email addresses.

### Demo Workflows Enabled

After seeding, you can demo:

1. **Investor Journey**:
   - Log in as investor1@demo.swadely.com
   - View existing holdings (MBO-2024, GIB-A24)
   - Subscribe to additional token series
   - Request redemptions

2. **Issuer Journey**:
   - Log in as issuer1@demo.swadely.com
   - View assets and proposals
   - Create new tokenization proposals
   - Upload disclosure documents

3. **Compliance Review**:
   - Log in as compliance@demo.swadely.com
   - Review pending KYC submissions (investor2)
   - Review AML alerts
   - Approve/reject redemption requests

4. **Admin Operations**:
   - Log in as admin@demo.swadely.com
   - View all users and system activity
   - Monitor audit logs
   - Suspend/activate users

### Troubleshooting

**Error: DATABASE_URL not set**
- Make sure `.env` file exists in `backend/` directory with `DATABASE_URL` set
- Or export `DATABASE_URL` environment variable before running

**Error: Connection refused**
- Ensure the database server is running
- Check that the DATABASE_URL hostname/port are correct
- Verify credentials are valid

**Error: Foreign key constraint violation**
- The script deletes demo data in proper FK order
- If this fails, there may be non-demo data referencing demo data
- Check for any manual data creation that references demo users
