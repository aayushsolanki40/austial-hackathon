"""``TokenizationProposal`` entity -- Phase 4.

The state-machine root of the issuance workflow (``AUSTIAL_BUILD_PLAN.md`` Phase 4)::

    DRAFT -> DOCUMENTATION_REVIEW -> COMPLIANCE_APPROVED -> IFSCA_FILED
          -> IFSCA_APPROVED -> LAUNCHED
                            \\-> REJECTED (terminal)

Every transition is guarded by ``IssuanceService``'s ``ALLOWED_TRANSITIONS`` table (an illegal
jump raises ``ConflictException`` rather than silently applying, mirroring ``KycService``'s and
``IssuersService``'s identical convention) and is written to ``AuditLog`` directly, in addition to
the generic global ``AuditInterceptor`` row every mutating request already produces.

★ Tokenization-readiness gate (see ``AUSTIAL_BUILD_PLAN.md``'s domain-model note in Section 1 and
this phase's own task brief): a proposal can only ever be created against an ``Asset`` whose
``custodian_verified`` is already ``True`` -- enforced in ``IssuanceService.create_proposal``,
*not* here or via a DB constraint, since (unlike ``Asset``/``Custodian``'s composite-FK trick)
there is no later mutation that could un-verify an already-attached custodian (``AssetsService``
exposes no "detach custodian" operation, and ``CustodiansService`` exposes no "un-verify"
operation either) -- so a one-time check at proposal creation is sufficient to guarantee
``LAUNCHED`` is unreachable for a non-tokenization-ready asset, without needing a second,
redundant DB-level constraint the way ``Asset``'s custodian attachment did. ``IssuanceService.
launch`` re-checks it anyway, defensively, in case either of those services ever grows a
detach/un-verify operation in a later phase -- see that method's docstring.

Money rule (``AUSTIAL_BUILD_PLAN.md`` Section 1): ``total_units``/``unit_price_usd``/
``min_subscription_units`` are all ``Numeric``, never ``Float`` -- exact decimal storage, no
binary-floating-point rounding error on financial quantities. Mirrors the plan's own
``TokenHolding.quantity``/``avg_cost_usd`` sketch, including its ``float`` Python-side type
annotation convention (the DB column type, not the Python attribute type, is what the money rule
actually governs).
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import (
    Column,
    CreateDateColumn,
    DateTime,
    Entity,
    EnumType,
    ManyToOne,
    Numeric,
    PrimaryGeneratedColumn,
    UpdateDateColumn,
)

from src.modules.assets.entities.asset import Asset
from src.modules.issuers.entities.issuer import Issuer

PROPOSAL_STATUSES = (
    "DRAFT",
    "DOCUMENTATION_REVIEW",
    "COMPLIANCE_APPROVED",
    "IFSCA_FILED",
    "IFSCA_APPROVED",
    "LAUNCHED",
    "REJECTED",
)


@Entity()
class TokenizationProposal:
    id: int = PrimaryGeneratedColumn()
    asset: Asset = ManyToOne(lambda: Asset, inverse_side="tokenization_proposals", nullable=False)
    # The submitting `Issuer` -- always the same organisation as `asset.issuer` (checked in
    # `IssuanceService.create_proposal`), kept as its own FK rather than derived through `asset`
    # so every proposal-scoped query/ownership check stays a single-hop join, mirroring `Asset`
    # carrying its own `issuer` FK rather than only being reachable through some other relation.
    issuer: Issuer = ManyToOne(lambda: Issuer, inverse_side="tokenization_proposals", nullable=False)

    total_units: float = Column(type_=Numeric(precision=28, scale=8))
    unit_price_usd: float = Column(type_=Numeric(precision=18, scale=2))
    min_subscription_units: float = Column(type_=Numeric(precision=28, scale=8))

    subscription_start_at: datetime = Column(type_=DateTime())
    subscription_end_at: datetime = Column(type_=DateTime())

    status: str = Column(type_=EnumType(values=PROPOSAL_STATUSES), default="DRAFT")

    # Populated by `IssuanceService.file_with_ifsca`/`ifsca_approve` -- these record a *manual/
    # simulated* regulatory filing/approval (no real IFSCA API exists to call), not proof of an
    # actual external transaction. See `IssuanceService`'s module docstring.
    ifsca_filing_reference: str = Column(nullable=True)
    ifsca_approval_reference: str = Column(nullable=True)
    rejection_reason: str = Column(nullable=True)
    reviewed_by_user_id: int = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
