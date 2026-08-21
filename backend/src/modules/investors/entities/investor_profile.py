"""``InvestorProfile`` entity -- Phase-1.5 **minimal stub**.

``InvestorProfile`` is formally a Phase 2 entity (see
``AUSTIAL_BUILD_PLAN.md``'s domain model: investor type, jurisdiction, risk
profile, ``kyc_status``). This stub exists *only* so ``KycVerifiedGuard`` has
something real to query against in Phase 1 -- it carries just enough fields
for that guard to function.

Phase 2 will extend this same entity with the full investor-profile field set
(investor type, jurisdiction, risk profile, ``WalletMapping`` relation, etc.).
Do not add those fields here now -- that's out of this phase's scope.
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, EnumType, ManyToOne, PrimaryGeneratedColumn, UpdateDateColumn

from src.modules.auth.entities.user import User

KYC_STATUSES = ("PENDING", "VERIFIED", "REJECTED")


@Entity()
class InvestorProfile:
    id: int = PrimaryGeneratedColumn()
    user: User = ManyToOne(lambda: User, inverse_side="investor_profile")
    kyc_status: str = Column(type_=EnumType(values=KYC_STATUSES), default="PENDING")
    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
