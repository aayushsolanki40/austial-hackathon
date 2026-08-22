"""Seed comprehensive demo data for all user roles.

Creates realistic demo data across all domains:
- Users for all 4 roles (INVESTOR, ISSUER, COMPLIANCE_OFFICER, ADMIN)
- Complete investor/issuer profiles with KYC data
- Assets, custodians, tokenization proposals
- Subscriptions, holdings, ledger accounts
- NAV feeds, redemption requests, AML alerts
- Audit logs showing system activity

Usage:
    # Local database (uses DATABASE_URL from .env)
    cd backend && uv run python scripts/seed_demo_data.py

    # Production database (override DATABASE_URL)
    DATABASE_URL=<prod-url> uv run python scripts/seed_demo_data.py

Demo credentials (all use password: Demo123!):
    - investor1@demo.swadely.com (APPROVED KYC)
    - investor2@demo.swadely.com (PENDING KYC)
    - investor3@demo.swadely.com (REJECTED KYC)
    - issuer1@demo.swadely.com (VERIFIED issuer)
    - issuer2@demo.swadely.com (PENDING issuer)
    - compliance@demo.swadely.com (Compliance Officer)
    - admin@demo.swadely.com (Admin)
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Add backend directory to path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Import all entities
from src.db.entities import ALL_ENTITIES
from src.modules.auth.entities.user import User
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.investors.entities.wallet_mapping import WalletMapping
from src.modules.issuers.entities.issuer import Issuer
from src.modules.custodians.entities.custodian import Custodian
from src.modules.assets.entities.asset import Asset
from src.modules.issuance.entities.tokenization_proposal import TokenizationProposal
from src.modules.issuance.entities.token_series import TokenSeries
from src.modules.issuance.entities.disclosure_document import DisclosureDocument
from src.modules.kyc.entities.kyc_submission import KycSubmission
from src.modules.kyc.entities.risk_disclosure_consent import RiskDisclosureConsent
from src.modules.ledger.entities.ledger_account import LedgerAccount
from src.modules.ledger.entities.ledger_entry import LedgerEntry
from src.modules.ledger.entities.funding_instruction import FundingInstruction
from src.modules.subscriptions.entities.subscription import Subscription
from src.modules.holdings.entities.token_holding import TokenHolding
from src.modules.valuation.entities.valuation_feed import ValuationFeed
from src.modules.redemptions.entities.redemption_request import RedemptionRequest
from src.modules.compliance.entities.aml_alert import AmlAlert
from src.modules.compliance.entities.audit_log import AuditLog

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Demo password for all users
DEMO_PASSWORD = "Demo123!"
DEMO_PASSWORD_HASH = _pwd_context.hash(DEMO_PASSWORD)


async def check_existing_demo_data(session: AsyncSession) -> bool:
    """Check if demo data already exists."""
    result = await session.execute(
        text("SELECT COUNT(*) FROM \"user\" WHERE email LIKE '%@demo.swadely.com'")
    )
    count = result.scalar()
    return count > 0


async def seed_data(session: AsyncSession):
    """Seed all demo data."""
    print("\n" + "=" * 60)
    print("SWADELY DEMO DATA SEED SCRIPT")
    print("=" * 60)

    # Check for existing data
    if await check_existing_demo_data(session):
        print("\n⚠️  Demo data already exists!")
        response = input("Delete and recreate? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            return
        await clear_demo_data(session)

    print("\n📝 Creating demo data...\n")

    # Track created entities for summary
    created = {
        "users": [],
        "investors": [],
        "issuers": [],
        "custodians": [],
        "assets": [],
        "proposals": [],
        "token_series": [],
        "subscriptions": [],
        "holdings": [],
        "redemptions": [],
        "aml_alerts": [],
    }

    # =========================================================================
    # 1. CREATE USERS
    # =========================================================================
    print("1️⃣  Creating users...")

    # INVESTORS (3 users with different KYC statuses)
    investor1_user = User()
    investor1_user.email = "investor1@demo.swadely.com"
    investor1_user.password_hash = DEMO_PASSWORD_HASH
    investor1_user.role = "INVESTOR"
    investor1_user.is_active = True
    session.add(investor1_user)
    await session.flush()
    created["users"].append(("investor1@demo.swadely.com", "INVESTOR", "APPROVED KYC"))

    investor2_user = User()
    investor2_user.email = "investor2@demo.swadely.com"
    investor2_user.password_hash = DEMO_PASSWORD_HASH
    investor2_user.role = "INVESTOR"
    investor2_user.is_active = True
    session.add(investor2_user)
    await session.flush()
    created["users"].append(("investor2@demo.swadely.com", "INVESTOR", "PENDING KYC"))

    investor3_user = User()
    investor3_user.email = "investor3@demo.swadely.com"
    investor3_user.password_hash = DEMO_PASSWORD_HASH
    investor3_user.role = "INVESTOR"
    investor3_user.is_active = True
    session.add(investor3_user)
    await session.flush()
    created["users"].append(("investor3@demo.swadely.com", "INVESTOR", "REJECTED KYC"))

    # ISSUERS (2 users with different verification statuses)
    issuer1_user = User()
    issuer1_user.email = "issuer1@demo.swadely.com"
    issuer1_user.password_hash = DEMO_PASSWORD_HASH
    issuer1_user.role = "ISSUER"
    issuer1_user.is_active = True
    session.add(issuer1_user)
    await session.flush()
    created["users"].append(("issuer1@demo.swadely.com", "ISSUER", "VERIFIED"))

    issuer2_user = User()
    issuer2_user.email = "issuer2@demo.swadely.com"
    issuer2_user.password_hash = DEMO_PASSWORD_HASH
    issuer2_user.role = "ISSUER"
    issuer2_user.is_active = True
    session.add(issuer2_user)
    await session.flush()
    created["users"].append(("issuer2@demo.swadely.com", "ISSUER", "PENDING"))

    # COMPLIANCE OFFICER
    compliance_user = User()
    compliance_user.email = "compliance@demo.swadely.com"
    compliance_user.password_hash = DEMO_PASSWORD_HASH
    compliance_user.role = "COMPLIANCE_OFFICER"
    compliance_user.is_active = True
    session.add(compliance_user)
    await session.flush()
    created["users"].append(("compliance@demo.swadely.com", "COMPLIANCE_OFFICER", "Active"))

    # ADMIN
    admin_user = User()
    admin_user.email = "admin@demo.swadely.com"
    admin_user.password_hash = DEMO_PASSWORD_HASH
    admin_user.role = "ADMIN"
    admin_user.is_active = True
    session.add(admin_user)
    await session.flush()
    created["users"].append(("admin@demo.swadely.com", "ADMIN", "Active"))

    await session.commit()
    print(f"   ✓ Created {len(created['users'])} users")

    # =========================================================================
    # 2. CREATE INVESTOR PROFILES + KYC
    # =========================================================================
    print("\n2️⃣  Creating investor profiles and KYC data...")

    # Investor 1: APPROVED KYC
    investor1_profile = InvestorProfile()
    investor1_profile.user = investor1_user
    investor1_profile.jurisdiction = "US"
    investor1_profile.investor_type = "INDIVIDUAL"
    investor1_profile.risk_profile = "MODERATE"
    investor1_profile.kyc_status = "VERIFIED"
    session.add(investor1_profile)
    await session.flush()

    kyc1 = KycSubmission()
    kyc1.investor = investor1_profile
    kyc1.legal_name = "Alice Johnson"
    kyc1.date_of_birth = datetime(1985, 6, 15).date()
    kyc1.nationality = "US"
    kyc1.status = "VERIFIED"
    kyc1.submitted_at = datetime.now(UTC) - timedelta(days=30)
    kyc1.screening_result = {
        "liveness": {"passed": True, "score": 0.95},
        "sanctions": {"matches": [], "cleared": True},
    }
    kyc1.reviewed_by_user_id = compliance_user.id
    kyc1.review_notes = "All checks passed. Documents verified."
    session.add(kyc1)

    risk_consent1 = RiskDisclosureConsent()
    risk_consent1.submission = kyc1
    risk_consent1.disclosure_version = "v1.0-2024"
    risk_consent1.ip_address = "203.0.113.42"
    session.add(risk_consent1)

    wallet1 = WalletMapping()
    wallet1.investor = investor1_profile
    wallet1.chain = "ETHEREUM"
    wallet1.address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1"
    wallet1.label = "Primary Wallet"
    wallet1.status = "ACTIVE"
    session.add(wallet1)

    created["investors"].append(("Alice Johnson", "VERIFIED", "US", "MODERATE"))

    # Investor 2: PENDING KYC
    investor2_profile = InvestorProfile()
    investor2_profile.user = investor2_user
    investor2_profile.jurisdiction = "SG"
    investor2_profile.investor_type = "INDIVIDUAL"
    investor2_profile.risk_profile = "AGGRESSIVE"
    investor2_profile.kyc_status = "PENDING"
    session.add(investor2_profile)
    await session.flush()

    kyc2 = KycSubmission()
    kyc2.investor = investor2_profile
    kyc2.legal_name = "Bob Chen"
    kyc2.date_of_birth = datetime(1990, 3, 22).date()
    kyc2.nationality = "SG"
    kyc2.status = "MANUAL_REVIEW"
    kyc2.submitted_at = datetime.now(UTC) - timedelta(days=2)
    kyc2.screening_result = {
        "liveness": {"passed": True, "score": 0.88},
        "sanctions": {"matches": [], "cleared": True},
    }
    session.add(kyc2)

    created["investors"].append(("Bob Chen", "PENDING", "SG", "AGGRESSIVE"))

    # Investor 3: REJECTED KYC
    investor3_profile = InvestorProfile()
    investor3_profile.user = investor3_user
    investor3_profile.jurisdiction = "GB"
    investor3_profile.investor_type = "INDIVIDUAL"
    investor3_profile.risk_profile = "CONSERVATIVE"
    investor3_profile.kyc_status = "REJECTED"
    session.add(investor3_profile)
    await session.flush()

    kyc3 = KycSubmission()
    kyc3.investor = investor3_profile
    kyc3.legal_name = "Charlie Smith"
    kyc3.date_of_birth = datetime(1978, 11, 5).date()
    kyc3.nationality = "GB"
    kyc3.status = "REJECTED"
    kyc3.submitted_at = datetime.now(UTC) - timedelta(days=10)
    kyc3.screening_result = {
        "liveness": {"passed": False, "score": 0.42},
        "sanctions": {"matches": [], "cleared": True},
    }
    kyc3.reviewed_by_user_id = compliance_user.id
    kyc3.review_notes = "Liveness check failed. Document quality insufficient."
    session.add(kyc3)

    created["investors"].append(("Charlie Smith", "REJECTED", "GB", "CONSERVATIVE"))

    await session.commit()
    print(f"   ✓ Created {len(created['investors'])} investor profiles with KYC")

    # =========================================================================
    # 3. CREATE ISSUER PROFILES
    # =========================================================================
    print("\n3️⃣  Creating issuer profiles...")

    # Issuer 1: VERIFIED
    issuer1_profile = Issuer()
    issuer1_profile.user = issuer1_user
    issuer1_profile.legal_name = "Acme Real Estate SPV Ltd"
    issuer1_profile.registration_number = "ARE-GIFT-2024-001"
    issuer1_profile.registration_jurisdiction = "IN"
    issuer1_profile.verification_status = "VERIFIED"
    issuer1_profile.verified_by_user_id = compliance_user.id
    issuer1_profile.verified_at = datetime.now(UTC) - timedelta(days=20)
    session.add(issuer1_profile)
    await session.flush()
    created["issuers"].append(("Acme Real Estate SPV Ltd", "VERIFIED", "IN"))

    # Issuer 2: PENDING
    issuer2_profile = Issuer()
    issuer2_profile.user = issuer2_user
    issuer2_profile.legal_name = "TechCorp Bonds Issuer Pte Ltd"
    issuer2_profile.registration_number = "TCB-SG-2024-042"
    issuer2_profile.registration_jurisdiction = "SG"
    issuer2_profile.verification_status = "PENDING"
    session.add(issuer2_profile)
    await session.flush()
    created["issuers"].append(("TechCorp Bonds Issuer Pte Ltd", "PENDING", "SG"))

    await session.commit()
    print(f"   ✓ Created {len(created['issuers'])} issuer profiles")

    # =========================================================================
    # 4. CREATE CUSTODIANS
    # =========================================================================
    print("\n4️⃣  Creating custodians...")

    custodian1 = Custodian()
    custodian1.name = "GIFT City Securities Custodian Ltd"
    custodian1.ifsca_registration_no = "IFSCA-CUST-2024-001"
    custodian1.ifsca_verified = True
    custodian1.verified_by_user_id = compliance_user.id
    custodian1.verified_at = datetime.now(UTC) - timedelta(days=60)
    session.add(custodian1)
    await session.flush()
    created["custodians"].append(("GIFT City Securities Custodian Ltd", "VERIFIED"))

    custodian2 = Custodian()
    custodian2.name = "Prime Asset Custody Services"
    custodian2.ifsca_registration_no = "IFSCA-CUST-2024-007"
    custodian2.ifsca_verified = True
    custodian2.verified_by_user_id = compliance_user.id
    custodian2.verified_at = datetime.now(UTC) - timedelta(days=45)
    session.add(custodian2)
    await session.flush()
    created["custodians"].append(("Prime Asset Custody Services", "VERIFIED"))

    custodian3 = Custodian()
    custodian3.name = "Regional Trust & Custody Co"
    custodian3.ifsca_registration_no = "IFSCA-CUST-2024-012"
    custodian3.ifsca_verified = False
    session.add(custodian3)
    await session.flush()
    created["custodians"].append(("Regional Trust & Custody Co", "PENDING"))

    await session.commit()
    print(f"   ✓ Created {len(created['custodians'])} custodians")

    # =========================================================================
    # 5. CREATE ASSETS
    # =========================================================================
    print("\n5️⃣  Creating assets...")

    # Asset 1: Real Estate with verified custodian (tokenization-ready)
    asset1 = Asset()
    asset1.issuer = issuer1_profile
    asset1.custodian = custodian1
    asset1.name = "Mumbai Premium Office Tower"
    asset1.asset_class = "REAL_ESTATE"
    asset1.description = "Grade A commercial office building in Mumbai's Bandra-Kurla Complex, 150,000 sq ft, 85% leased to multinational tenants."
    asset1.custodian_verified = True
    session.add(asset1)
    await session.flush()
    created["assets"].append(("Mumbai Premium Office Tower", "REAL_ESTATE", "Tokenization Ready"))

    # Asset 2: Security (bond) with verified custodian
    asset2 = Asset()
    asset2.issuer = issuer1_profile
    asset2.custodian = custodian2
    asset2.name = "Green Infrastructure Bond Series A"
    asset2.asset_class = "SECURITY"
    asset2.description = "5-year senior secured bond financing renewable energy projects across India. 7.5% annual coupon, quarterly payments."
    asset2.custodian_verified = True
    session.add(asset2)
    await session.flush()
    created["assets"].append(("Green Infrastructure Bond Series A", "SECURITY", "Tokenization Ready"))

    # Asset 3: Real Estate without custodian (not tokenization-ready)
    asset3 = Asset()
    asset3.issuer = issuer1_profile
    asset3.name = "Singapore Residential Portfolio"
    asset3.asset_class = "REAL_ESTATE"
    asset3.description = "Diversified portfolio of 12 residential properties in Singapore prime districts."
    asset3.custodian_verified = False
    session.add(asset3)
    await session.flush()
    created["assets"].append(("Singapore Residential Portfolio", "REAL_ESTATE", "No Custodian"))

    # Asset 4: Commodity
    asset4 = Asset()
    asset4.issuer = issuer1_profile
    asset4.custodian = custodian1
    asset4.name = "Gold Bullion Reserve 2024"
    asset4.asset_class = "COMMODITY"
    asset4.description = "1000 oz of 99.99% pure gold bullion stored in GIFT City vault."
    asset4.custodian_verified = True
    session.add(asset4)
    await session.flush()
    created["assets"].append(("Gold Bullion Reserve 2024", "COMMODITY", "Tokenization Ready"))

    await session.commit()
    print(f"   ✓ Created {len(created['assets'])} assets")

    # =========================================================================
    # 6. CREATE TOKENIZATION PROPOSALS + TOKEN SERIES
    # =========================================================================
    print("\n6️⃣  Creating tokenization proposals and token series...")

    # Proposal 1: LAUNCHED (Mumbai Office Tower)
    proposal1 = TokenizationProposal()
    proposal1.asset = asset1
    proposal1.issuer = issuer1_profile
    proposal1.total_units = Decimal("10000.00000000")
    proposal1.unit_price_usd = Decimal("100.00")
    proposal1.min_subscription_units = Decimal("10.00000000")
    proposal1.subscription_start_at = datetime.now(UTC) - timedelta(days=30)
    proposal1.subscription_end_at = datetime.now(UTC) + timedelta(days=30)
    proposal1.status = "LAUNCHED"
    proposal1.ifsca_filing_reference = "IFSCA-FILE-2024-RE-001"
    proposal1.ifsca_approval_reference = "IFSCA-APPR-2024-RE-001"
    proposal1.reviewed_by_user_id = compliance_user.id
    session.add(proposal1)
    await session.flush()

    # Add all disclosure documents for proposal 1
    for doc_type in ["RISK", "FEE", "LIQUIDITY", "CUSTODY", "TAX", "PROSPECTUS"]:
        disclosure = DisclosureDocument()
        disclosure.proposal = proposal1
        disclosure.disclosure_type = doc_type
        disclosure.object_key = f"demo/disclosures/proposal-{proposal1.id}/{doc_type.lower()}-v1.pdf"
        disclosure.version = 1
        disclosure.is_current = True
        disclosure.uploaded_by_user_id = issuer1_user.id
        session.add(disclosure)

    # Token series for proposal 1
    token_series1 = TokenSeries()
    token_series1.proposal = proposal1
    token_series1.symbol = "MBO-2024"
    token_series1.total_supply = Decimal("10000.00000000")
    token_series1.contract_address = "0x1234567890abcdef1234567890abcdef12345678"
    token_series1.paused = False
    token_series1.launched_by_user_id = compliance_user.id
    session.add(token_series1)
    await session.flush()
    created["proposals"].append(("Mumbai Premium Office Tower", "LAUNCHED", "$100/unit"))
    created["token_series"].append(("MBO-2024", "10,000 units", "ACTIVE"))

    # Proposal 2: LAUNCHED (Green Infrastructure Bond)
    proposal2 = TokenizationProposal()
    proposal2.asset = asset2
    proposal2.issuer = issuer1_profile
    proposal2.total_units = Decimal("5000.00000000")
    proposal2.unit_price_usd = Decimal("1000.00")
    proposal2.min_subscription_units = Decimal("1.00000000")
    proposal2.subscription_start_at = datetime.now(UTC) - timedelta(days=15)
    proposal2.subscription_end_at = datetime.now(UTC) + timedelta(days=45)
    proposal2.status = "LAUNCHED"
    proposal2.ifsca_filing_reference = "IFSCA-FILE-2024-BOND-001"
    proposal2.ifsca_approval_reference = "IFSCA-APPR-2024-BOND-001"
    proposal2.reviewed_by_user_id = compliance_user.id
    session.add(proposal2)
    await session.flush()

    # Add disclosure documents
    for doc_type in ["RISK", "FEE", "LIQUIDITY", "CUSTODY", "TAX", "PROSPECTUS"]:
        disclosure = DisclosureDocument()
        disclosure.proposal = proposal2
        disclosure.disclosure_type = doc_type
        disclosure.object_key = f"demo/disclosures/proposal-{proposal2.id}/{doc_type.lower()}-v1.pdf"
        disclosure.version = 1
        disclosure.is_current = True
        disclosure.uploaded_by_user_id = issuer1_user.id
        session.add(disclosure)

    token_series2 = TokenSeries()
    token_series2.proposal = proposal2
    token_series2.symbol = "GIB-A24"
    token_series2.total_supply = Decimal("5000.00000000")
    token_series2.contract_address = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
    token_series2.paused = False
    token_series2.launched_by_user_id = compliance_user.id
    session.add(token_series2)
    await session.flush()
    created["proposals"].append(("Green Infrastructure Bond Series A", "LAUNCHED", "$1000/unit"))
    created["token_series"].append(("GIB-A24", "5,000 units", "ACTIVE"))

    # Proposal 3: COMPLIANCE_APPROVED (Gold Bullion)
    proposal3 = TokenizationProposal()
    proposal3.asset = asset4
    proposal3.issuer = issuer1_profile
    proposal3.total_units = Decimal("1000.00000000")
    proposal3.unit_price_usd = Decimal("2500.00")
    proposal3.min_subscription_units = Decimal("0.10000000")
    proposal3.subscription_start_at = datetime.now(UTC) + timedelta(days=7)
    proposal3.subscription_end_at = datetime.now(UTC) + timedelta(days=67)
    proposal3.status = "COMPLIANCE_APPROVED"
    proposal3.reviewed_by_user_id = compliance_user.id
    session.add(proposal3)
    await session.flush()

    # Partial disclosure documents (not all 6, so not launchable yet)
    for doc_type in ["RISK", "FEE", "CUSTODY"]:
        disclosure = DisclosureDocument()
        disclosure.proposal = proposal3
        disclosure.disclosure_type = doc_type
        disclosure.object_key = f"demo/disclosures/proposal-{proposal3.id}/{doc_type.lower()}-v1.pdf"
        disclosure.version = 1
        disclosure.is_current = True
        disclosure.uploaded_by_user_id = issuer1_user.id
        session.add(disclosure)

    created["proposals"].append(("Gold Bullion Reserve 2024", "COMPLIANCE_APPROVED", "$2500/unit"))

    # Proposal 4: DRAFT (Singapore portfolio - no custodian, can't proceed)
    proposal4 = TokenizationProposal()
    proposal4.asset = asset3
    proposal4.issuer = issuer1_profile
    proposal4.total_units = Decimal("20000.00000000")
    proposal4.unit_price_usd = Decimal("50.00")
    proposal4.min_subscription_units = Decimal("20.00000000")
    proposal4.subscription_start_at = datetime.now(UTC) + timedelta(days=30)
    proposal4.subscription_end_at = datetime.now(UTC) + timedelta(days=90)
    proposal4.status = "DRAFT"
    session.add(proposal4)
    await session.flush()
    created["proposals"].append(("Singapore Residential Portfolio", "DRAFT", "$50/unit"))

    await session.commit()
    print(f"   ✓ Created {len(created['proposals'])} tokenization proposals")
    print(f"   ✓ Created {len(created['token_series'])} token series")

    # =========================================================================
    # 7. CREATE LEDGER ACCOUNTS + FUNDING
    # =========================================================================
    print("\n7️⃣  Creating ledger accounts and funding...")

    # Investor 1 ledger account with balance
    ledger1 = LedgerAccount()
    ledger1.investor = investor1_profile
    ledger1.currency = "USD"
    ledger1.available_balance = Decimal("50000.00")
    ledger1.locked_balance = Decimal("0.00")
    session.add(ledger1)
    await session.flush()

    # Funding instruction for investor 1
    funding1 = FundingInstruction()
    funding1.investor = investor1_profile
    funding1.currency = "USD"
    funding1.amount = Decimal("50000.00")
    funding1.reference_code = f"WIRE-{uuid.uuid4().hex[:12].upper()}"
    funding1.status = "CONFIRMED"
    funding1.confirmed_by_user_id = compliance_user.id
    funding1.confirmed_at = datetime.now(UTC) - timedelta(days=28)
    session.add(funding1)
    await session.flush()

    # Ledger entry for funding
    entry1 = LedgerEntry()
    entry1.account = ledger1
    entry1.entry_type = "CREDIT_FUNDING"
    entry1.amount = Decimal("50000.00")
    entry1.currency = "USD"
    entry1.balance_after = Decimal("50000.00")
    entry1.reference_type = "FUNDING_INSTRUCTION"
    entry1.reference_id = funding1.id
    entry1.idempotency_key = str(uuid.uuid4())
    session.add(entry1)

    # Investor 2 ledger account with smaller balance
    ledger2 = LedgerAccount()
    ledger2.investor = investor2_profile
    ledger2.currency = "USD"
    ledger2.available_balance = Decimal("5000.00")
    ledger2.locked_balance = Decimal("0.00")
    session.add(ledger2)
    await session.flush()

    funding2 = FundingInstruction()
    funding2.investor = investor2_profile
    funding2.currency = "USD"
    funding2.amount = Decimal("5000.00")
    funding2.reference_code = f"WIRE-{uuid.uuid4().hex[:12].upper()}"
    funding2.status = "CONFIRMED"
    funding2.confirmed_by_user_id = compliance_user.id
    funding2.confirmed_at = datetime.now(UTC) - timedelta(days=5)
    session.add(funding2)
    await session.flush()

    entry2 = LedgerEntry()
    entry2.account = ledger2
    entry2.entry_type = "CREDIT_FUNDING"
    entry2.amount = Decimal("5000.00")
    entry2.currency = "USD"
    entry2.balance_after = Decimal("5000.00")
    entry2.reference_type = "FUNDING_INSTRUCTION"
    entry2.reference_id = funding2.id
    entry2.idempotency_key = str(uuid.uuid4())
    session.add(entry2)

    await session.commit()
    print(f"   ✓ Created 2 ledger accounts with funding")

    # =========================================================================
    # 8. CREATE SUBSCRIPTIONS + HOLDINGS
    # =========================================================================
    print("\n8️⃣  Creating subscriptions and holdings...")

    # Subscription 1: ALLOCATED (investor1 -> MBO-2024)
    sub1 = Subscription()
    sub1.investor = investor1_profile
    sub1.token_series = token_series1
    sub1.units = Decimal("100.00000000")
    sub1.amount_usd = Decimal("10000.00")
    sub1.allocated_units = Decimal("100.00000000")
    sub1.status = "ALLOCATED"
    sub1.risk_disclosure_accepted = True
    sub1.fee_disclosure_accepted = True
    sub1.disclosures_acknowledged_at = datetime.now(UTC) - timedelta(days=25)
    sub1.processed_by_user_id = compliance_user.id
    session.add(sub1)
    await session.flush()
    created["subscriptions"].append(("Alice Johnson", "MBO-2024", "100 units", "ALLOCATED"))

    # Holding for sub1
    holding1 = TokenHolding()
    holding1.investor = investor1_profile
    holding1.token_series = token_series1
    holding1.quantity = Decimal("100.00000000")
    holding1.avg_cost_usd = Decimal("100.00")
    holding1.status = "ACTIVE"
    holding1.custodian_confirmation_ref = f"CUST-CONF-{uuid.uuid4().hex[:8].upper()}"
    session.add(holding1)
    await session.flush()
    created["holdings"].append(("Alice Johnson", "MBO-2024", "100 units", "ACTIVE"))

    # Subscription 2: ALLOCATED (investor1 -> GIB-A24)
    sub2 = Subscription()
    sub2.investor = investor1_profile
    sub2.token_series = token_series2
    sub2.units = Decimal("20.00000000")
    sub2.amount_usd = Decimal("20000.00")
    sub2.allocated_units = Decimal("20.00000000")
    sub2.status = "ALLOCATED"
    sub2.risk_disclosure_accepted = True
    sub2.fee_disclosure_accepted = True
    sub2.disclosures_acknowledged_at = datetime.now(UTC) - timedelta(days=12)
    sub2.processed_by_user_id = compliance_user.id
    session.add(sub2)
    await session.flush()
    created["subscriptions"].append(("Alice Johnson", "GIB-A24", "20 units", "ALLOCATED"))

    holding2 = TokenHolding()
    holding2.investor = investor1_profile
    holding2.token_series = token_series2
    holding2.quantity = Decimal("20.00000000")
    holding2.avg_cost_usd = Decimal("1000.00")
    holding2.status = "ACTIVE"
    holding2.custodian_confirmation_ref = f"CUST-CONF-{uuid.uuid4().hex[:8].upper()}"
    session.add(holding2)
    await session.flush()
    created["holdings"].append(("Alice Johnson", "GIB-A24", "20 units", "ACTIVE"))

    # Subscription 3: PENDING (investor2 -> MBO-2024)
    sub3 = Subscription()
    sub3.investor = investor2_profile
    sub3.token_series = token_series1
    sub3.units = Decimal("50.00000000")
    sub3.amount_usd = Decimal("5000.00")
    sub3.status = "PENDING"
    sub3.risk_disclosure_accepted = True
    sub3.fee_disclosure_accepted = True
    sub3.disclosures_acknowledged_at = datetime.now(UTC) - timedelta(hours=2)
    session.add(sub3)
    await session.flush()
    created["subscriptions"].append(("Bob Chen", "MBO-2024", "50 units", "PENDING"))

    await session.commit()
    print(f"   ✓ Created {len(created['subscriptions'])} subscriptions")
    print(f"   ✓ Created {len(created['holdings'])} holdings")

    # =========================================================================
    # 9. CREATE NAV FEEDS
    # =========================================================================
    print("\n9️⃣  Creating NAV feeds...")

    # NAV feeds for token_series1 (MBO-2024) - showing gradual appreciation
    for days_ago in [20, 15, 10, 5, 1]:
        nav = ValuationFeed()
        nav.token_series = token_series1
        nav.nav_per_unit = Decimal("100.00") + Decimal(str((20 - days_ago) * 0.5))
        nav.source = "Independent Valuator - PropValue India"
        nav.status = "PUBLISHED"
        nav.reported_at = datetime.now(UTC) - timedelta(days=days_ago)
        nav.anomaly_score = None if days_ago == 20 else 0.01
        session.add(nav)

    # NAV feeds for token_series2 (GIB-A24) - stable bond
    for days_ago in [14, 10, 7, 3]:
        nav = ValuationFeed()
        nav.token_series = token_series2
        nav.nav_per_unit = Decimal("1000.00") + Decimal(str((14 - days_ago) * 0.2))
        nav.source = "Bond Pricing Service - GIFT City Markets"
        nav.status = "PUBLISHED"
        nav.reported_at = datetime.now(UTC) - timedelta(days=days_ago)
        nav.anomaly_score = 0.005
        session.add(nav)

    await session.commit()
    print(f"   ✓ Created NAV feeds for token series")

    # =========================================================================
    # 10. CREATE REDEMPTION REQUESTS
    # =========================================================================
    print("\n🔟  Creating redemption requests...")

    # Redemption 1: REQUESTED (investor1 wants to redeem 20 units of GIB-A24)
    redemption1 = RedemptionRequest()
    redemption1.investor = investor1_profile
    redemption1.holding = holding2
    redemption1.units_requested = Decimal("5.00000000")
    redemption1.status = "REQUESTED"
    session.add(redemption1)
    await session.flush()
    created["redemptions"].append(("Alice Johnson", "GIB-A24", "5 units", "REQUESTED"))

    # Redemption 2: COMPLETED (investor1 redeemed 10 units of MBO-2024 earlier)
    redemption2 = RedemptionRequest()
    redemption2.investor = investor1_profile
    redemption2.holding = holding1
    redemption2.units_requested = Decimal("10.00000000")
    redemption2.nav_per_unit_snapshot = Decimal("108.50")
    redemption2.payout_amount = Decimal("1085.00")
    redemption2.status = "COMPLETED"
    redemption2.processed_by_user_id = compliance_user.id
    session.add(redemption2)
    await session.flush()
    created["redemptions"].append(("Alice Johnson", "MBO-2024", "10 units", "COMPLETED"))

    await session.commit()
    print(f"   ✓ Created {len(created['redemptions'])} redemption requests")

    # =========================================================================
    # 11. CREATE AML ALERTS
    # =========================================================================
    print("\n1️⃣1️⃣  Creating AML alerts...")

    # AML Alert 1: OPEN (large transaction for investor1)
    aml1 = AmlAlert()
    aml1.transaction_ref = f"TXN-{uuid.uuid4().hex[:12].upper()}"
    aml1.investor = investor1_profile
    aml1.alert_type = "LARGE_TRANSACTION"
    aml1.risk_score = Decimal("65.50")
    aml1.status = "OPEN"
    aml1.rule_triggered = "AMOUNT_THRESHOLD_50K"
    session.add(aml1)
    created["aml_alerts"].append(("Alice Johnson", "LARGE_TRANSACTION", "OPEN"))

    # AML Alert 2: UNDER_REVIEW (rapid succession for investor2)
    aml2 = AmlAlert()
    aml2.transaction_ref = f"TXN-{uuid.uuid4().hex[:12].upper()}"
    aml2.investor = investor2_profile
    aml2.alert_type = "RAPID_SUCCESSION"
    aml2.risk_score = Decimal("45.30")
    aml2.status = "UNDER_REVIEW"
    aml2.rule_triggered = "MULTIPLE_TX_1H"
    aml2.assigned_officer = compliance_user
    session.add(aml2)
    created["aml_alerts"].append(("Bob Chen", "RAPID_SUCCESSION", "UNDER_REVIEW"))

    # AML Alert 3: DISMISSED
    aml3 = AmlAlert()
    aml3.transaction_ref = f"TXN-{uuid.uuid4().hex[:12].upper()}"
    aml3.investor = investor1_profile
    aml3.alert_type = "ANOMALY"
    aml3.risk_score = Decimal("32.10")
    aml3.status = "DISMISSED"
    aml3.rule_triggered = "PATTERN_DEVIATION"
    aml3.assigned_officer = compliance_user
    aml3.resolution_notes = "False positive. Transaction verified with investor."
    aml3.resolved_at = datetime.now(UTC) - timedelta(days=3)
    session.add(aml3)
    created["aml_alerts"].append(("Alice Johnson", "ANOMALY", "DISMISSED"))

    await session.commit()
    print(f"   ✓ Created {len(created['aml_alerts'])} AML alerts")

    # =========================================================================
    # 12. CREATE AUDIT LOGS
    # =========================================================================
    print("\n1️⃣2️⃣  Creating audit logs...")

    # Sample audit logs showing various system activities
    audit_events = [
        ("USER_REGISTRATION", "User", str(investor1_user.id), investor1_user.id),
        ("KYC_SUBMITTED", "KycSubmission", str(kyc1.id), investor1_user.id),
        ("KYC_VERIFIED", "KycSubmission", str(kyc1.id), compliance_user.id),
        ("ISSUER_VERIFIED", "Issuer", str(issuer1_profile.id), compliance_user.id),
        ("ASSET_CREATED", "Asset", str(asset1.id), issuer1_user.id),
        ("PROPOSAL_LAUNCHED", "TokenizationProposal", str(proposal1.id), compliance_user.id),
        ("SUBSCRIPTION_CREATED", "Subscription", str(sub1.id), investor1_user.id),
        ("SUBSCRIPTION_ALLOCATED", "Subscription", str(sub1.id), compliance_user.id),
        ("REDEMPTION_REQUESTED", "RedemptionRequest", str(redemption1.id), investor1_user.id),
        ("AML_ALERT_CREATED", "AmlAlert", str(aml1.id), None),
    ]

    for action, entity_type, entity_id, actor_id in audit_events:
        audit = AuditLog()
        audit.actor_user_id = actor_id
        audit.action = action
        audit.entity_type = entity_type
        audit.entity_id = entity_id
        audit.before_state = None
        audit.after_state = {"demo": True}
        audit.ip_address = "203.0.113.42"
        session.add(audit)

    await session.commit()
    print(f"   ✓ Created {len(audit_events)} audit log entries")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 60)
    print("✅ SEED COMPLETE!")
    print("=" * 60)

    print("\n📊 CREATED DATA SUMMARY:\n")

    print("👥 USERS (password for all: Demo123!):")
    for email, role, status in created["users"]:
        print(f"   • {email:<35} {role:<20} {status}")

    print("\n💼 INVESTORS:")
    for name, kyc_status, jurisdiction, risk in created["investors"]:
        print(f"   • {name:<25} KYC: {kyc_status:<10} {jurisdiction}  Risk: {risk}")

    print("\n🏢 ISSUERS:")
    for name, status, jurisdiction in created["issuers"]:
        print(f"   • {name:<40} {status:<10} {jurisdiction}")

    print("\n🏦 CUSTODIANS:")
    for name, status in created["custodians"]:
        print(f"   • {name:<45} {status}")

    print("\n🏗️  ASSETS:")
    for name, asset_class, status in created["assets"]:
        print(f"   • {name:<45} {asset_class:<15} {status}")

    print("\n📋 TOKENIZATION PROPOSALS:")
    for name, status, price in created["proposals"]:
        print(f"   • {name:<45} {status:<25} {price}")

    print("\n🎫 TOKEN SERIES:")
    for symbol, supply, status in created["token_series"]:
        print(f"   • {symbol:<15} {supply:<20} {status}")

    print("\n💰 SUBSCRIPTIONS:")
    for investor, series, units, status in created["subscriptions"]:
        print(f"   • {investor:<25} → {series:<15} {units:<15} {status}")

    print("\n📦 HOLDINGS:")
    for investor, series, quantity, status in created["holdings"]:
        print(f"   • {investor:<25} → {series:<15} {quantity:<15} {status}")

    print("\n🔄 REDEMPTION REQUESTS:")
    for investor, series, units, status in created["redemptions"]:
        print(f"   • {investor:<25} → {series:<15} {units:<15} {status}")

    print("\n🚨 AML ALERTS:")
    for investor, alert_type, status in created["aml_alerts"]:
        print(f"   • {investor:<25} {alert_type:<25} {status}")

    print("\n" + "=" * 60)
    print("🚀 DEMO ENVIRONMENT READY")
    print("=" * 60)
    print("\nYou can now log in with any of the demo accounts above.")
    print("All accounts use password: Demo123!\n")


async def clear_demo_data(session: AsyncSession):
    """Delete all demo data (users with @demo.swadely.com emails)."""
    print("\n🗑️  Deleting existing demo data...")

    # Delete in reverse FK dependency order
    await session.execute(text("DELETE FROM audit_log WHERE actor_user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com')"))
    await session.execute(text("DELETE FROM aml_alert WHERE investor_id IN (SELECT id FROM investor_profile WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com'))"))
    await session.execute(text("DELETE FROM redemption_request WHERE investor_id IN (SELECT id FROM investor_profile WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com'))"))
    await session.execute(text("DELETE FROM valuation_feed WHERE token_series_id IN (SELECT id FROM token_series WHERE proposal_id IN (SELECT id FROM tokenization_proposal WHERE issuer_id IN (SELECT id FROM issuer WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com'))))"))
    await session.execute(text("DELETE FROM token_holding WHERE investor_id IN (SELECT id FROM investor_profile WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com'))"))
    await session.execute(text("DELETE FROM subscription WHERE investor_id IN (SELECT id FROM investor_profile WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com'))"))
    await session.execute(text("DELETE FROM ledger_entry WHERE account_id IN (SELECT id FROM ledger_account WHERE investor_id IN (SELECT id FROM investor_profile WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com')))"))
    await session.execute(text("DELETE FROM funding_instruction WHERE investor_id IN (SELECT id FROM investor_profile WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com'))"))
    await session.execute(text("DELETE FROM ledger_account WHERE investor_id IN (SELECT id FROM investor_profile WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com'))"))
    await session.execute(text("DELETE FROM disclosure_document WHERE proposal_id IN (SELECT id FROM tokenization_proposal WHERE issuer_id IN (SELECT id FROM issuer WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com')))"))
    await session.execute(text("DELETE FROM token_series WHERE proposal_id IN (SELECT id FROM tokenization_proposal WHERE issuer_id IN (SELECT id FROM issuer WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com')))"))
    await session.execute(text("DELETE FROM tokenization_proposal WHERE issuer_id IN (SELECT id FROM issuer WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com'))"))
    await session.execute(text("DELETE FROM asset WHERE issuer_id IN (SELECT id FROM issuer WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com'))"))
    await session.execute(text("DELETE FROM custodian WHERE verified_by_user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com')"))
    await session.execute(text("DELETE FROM wallet_mapping WHERE investor_id IN (SELECT id FROM investor_profile WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com'))"))
    await session.execute(text("DELETE FROM risk_disclosure_consent WHERE investor_id IN (SELECT id FROM investor_profile WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com'))"))
    await session.execute(text("DELETE FROM kyc_document WHERE submission_id IN (SELECT id FROM kyc_submission WHERE investor_id IN (SELECT id FROM investor_profile WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com')))"))
    await session.execute(text("DELETE FROM kyc_submission WHERE investor_id IN (SELECT id FROM investor_profile WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com'))"))
    await session.execute(text("DELETE FROM issuer WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com')"))
    await session.execute(text("DELETE FROM investor_profile WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com')"))
    await session.execute(text("DELETE FROM refresh_token WHERE user_id IN (SELECT id FROM \"user\" WHERE email LIKE '%@demo.swadely.com')"))
    await session.execute(text("DELETE FROM \"user\" WHERE email LIKE '%@demo.swadely.com'"))

    await session.commit()
    print("   ✓ Demo data cleared")


async def main():
    """Main entry point."""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        print("\nUsage:")
        print("  # Local: cd backend && uv run python scripts/seed_demo_data.py")
        print("  # Production: DATABASE_URL=<url> uv run python scripts/seed_demo_data.py")
        sys.exit(1)

    print(f"\n🔗 Connecting to: {database_url[:50]}...")

    # Create async engine
    engine = create_async_engine(database_url, echo=False)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            await seed_data(session)
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            sys.exit(1)
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
