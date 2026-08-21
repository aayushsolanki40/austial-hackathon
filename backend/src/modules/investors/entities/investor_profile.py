"""``InvestorProfile`` entity -- Phase 2.

Extends the Phase-1.5 minimal stub (``id``, ``user``, ``kyc_status``,
timestamps) with the full investor-profile field set from
``AUSTIAL_BUILD_PLAN.md``'s domain model: investor type, jurisdiction, risk
profile.

★ Regulatory note: this entity intentionally does **not** carry a chain
wallet address column, or raw KYC-identity PII (legal name, date of birth,
document numbers). Wallet addresses live on the separate ``WalletMapping``
table (see that module's docstring for the "PII never co-located with chain
addresses" rule), and identity PII lives on ``KycSubmission``
(``src/modules/kyc/``) -- this entity only carries the *investor
classification* fields a compliance/product surface needs (type,
jurisdiction, risk profile, KYC status), not raw personal data.
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, EnumType, ManyToOne, PrimaryGeneratedColumn, UpdateDateColumn

from src.modules.auth.entities.user import User

KYC_STATUSES = ("PENDING", "VERIFIED", "REJECTED")

# Individual vs. institutional investor -- drives disclosure/suitability rules downstream
# (Phase 6+); kept as a small closed set rather than free text.
INVESTOR_TYPES = ("INDIVIDUAL", "INSTITUTIONAL")

# Investor's declared risk appetite, captured during onboarding's risk-disclosure step
# (see the build plan's frontend note on "risk disclosure with signed consent record").
RISK_PROFILES = ("CONSERVATIVE", "MODERATE", "AGGRESSIVE")


@Entity()
class InvestorProfile:
    id: int = PrimaryGeneratedColumn()
    user: User = ManyToOne(lambda: User, inverse_side="investor_profile")

    # ISO 3166-1 alpha-2 country code of tax/legal residence (e.g. "IN", "US") -- validated at
    # the DTO layer (see `investors_dto.py`), stored as the plain 2-letter code here.
    jurisdiction: str = Column(nullable=True)
    investor_type: str = Column(type_=EnumType(values=INVESTOR_TYPES), nullable=True)
    risk_profile: str = Column(type_=EnumType(values=RISK_PROFILES), nullable=True)

    kyc_status: str = Column(type_=EnumType(values=KYC_STATUSES), default="PENDING")
    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
