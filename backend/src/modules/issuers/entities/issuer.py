"""``Issuer`` entity -- Phase 3.

An issuer *organisation* record, one-to-one with a ``User`` of role
``ISSUER`` (enforced in the service layer, mirroring ``InvestorProfile``'s
identical "one profile per user, checked in ``IssuersService``, not via a DB
``unique`` constraint on the relation" convention -- ``ManyToOne`` has no
``unique=`` option in ``austial.orm`` today, same limitation that pattern
already works around).

Carries the fit-and-proper verification fields ``AUSTIAL_BUILD_PLAN.md``
Phase 3 calls for: legal identity/registration details plus a
``verification_status`` a ``COMPLIANCE_OFFICER`` moves ``PENDING ->
VERIFIED | REJECTED`` (single-hop, terminal -- unlike ``KycSubmission``'s
multi-stage machine, there's no automated screening step here, just a human
fit-and-proper review, so one transition each way is enough for Phase 3).

Deliberately does **not** gate ``AssetsService.create_asset`` on
``verification_status == VERIFIED`` -- Phase 4's ``issuance`` module owns the
real compliance-approval pipeline (``DRAFT -> ... -> LAUNCHED``) an asset's
*tokenization proposal* must pass; an issuer's own fit-and-proper status is a
prerequisite an ops/compliance workflow checks before letting that pipeline
proceed, not a second, redundant gate hard-coded into asset submission here.
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, EnumType, ManyToOne, PrimaryGeneratedColumn, UpdateDateColumn

from src.modules.auth.entities.user import User

ISSUER_VERIFICATION_STATUSES = ("PENDING", "VERIFIED", "REJECTED")


@Entity()
class Issuer:
    id: int = PrimaryGeneratedColumn()
    user: User = ManyToOne(lambda: User, inverse_side="issuer_profile", nullable=False)

    legal_name: str = Column()
    # Company/LEI-style registration number issued by the issuer's home regulator/registrar --
    # free text (formats vary by jurisdiction), validated for non-emptiness at the DTO layer.
    registration_number: str = Column()
    # ISO 3166-1 alpha-2 jurisdiction of incorporation/registration -- validated at the DTO layer,
    # mirrors `InvestorProfile.jurisdiction`'s "plain 2-letter code stored here" convention.
    registration_jurisdiction: str = Column()

    verification_status: str = Column(type_=EnumType(values=ISSUER_VERIFICATION_STATUSES), default="PENDING")
    verified_by_user_id: int = Column(nullable=True)
    verified_at: datetime = Column(nullable=True)
    rejection_reason: str = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
