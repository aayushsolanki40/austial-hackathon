"""``KycSubmission`` entity -- Phase 2.

Owns the applicant-declared identity fields (legal name, date of birth,
nationality) -- this is the one place raw KYC PII legitimately lives, kept
deliberately separate from ``InvestorProfile`` (investor classification
only) and ``WalletMapping`` (chain addresses only, no PII) -- see both of
those entities' docstrings for the "PII never co-located with chain
addresses" rule this split reinforces.

Status machine (enforced in ``kyc_service.py``, not here -- an entity has no
business logic in this framework's convention, see ``AuditLog``'s own
docstring for the same "entity is just a mapped table" idiom)::

    DRAFT -> SUBMITTED -> AUTO_SCREENING -> MANUAL_REVIEW -> VERIFIED | REJECTED

``screening_result`` accumulates the mock liveness/face-match + sanctions
screening output (``KycService._run_auto_screening_pipeline``) as one JSON
blob; each ``KycDocument`` carries its own OCR result independently (see
that entity).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from austial.orm import (
    Column,
    CreateDateColumn,
    Entity,
    EnumType,
    JSONType,
    ManyToOne,
    PrimaryGeneratedColumn,
    UpdateDateColumn,
)

from src.modules.investors.entities.investor_profile import InvestorProfile

KYC_SUBMISSION_STATUSES = (
    "DRAFT",
    "SUBMITTED",
    "AUTO_SCREENING",
    "MANUAL_REVIEW",
    "VERIFIED",
    "REJECTED",
)


@Entity()
class KycSubmission:
    id: int = PrimaryGeneratedColumn()
    investor: InvestorProfile = ManyToOne(lambda: InvestorProfile, inverse_side="kyc_submissions", nullable=False)

    status: str = Column(type_=EnumType(values=KYC_SUBMISSION_STATUSES), default="DRAFT")

    # Applicant-declared identity, captured at submission creation.
    legal_name: str = Column()
    date_of_birth: date = Column()
    nationality: str = Column()  # ISO 3166-1 alpha-2, validated at the DTO layer

    submitted_at: datetime = Column(nullable=True)

    # Aggregated mock auto-screening output (liveness/face-match + sanctions) -- see
    # `src/modules/kyc/providers/` for the swappable provider interfaces behind this.
    screening_result: dict[str, Any] = Column(type_=JSONType(), nullable=True)

    reviewed_by_user_id: int = Column(nullable=True)
    review_notes: str = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
