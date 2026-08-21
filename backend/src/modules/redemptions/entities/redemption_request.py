from __future__ import annotations

from datetime import datetime

from austial.orm import (
    Column,
    CreateDateColumn,
    Entity,
    EnumType,
    ManyToOne,
    Numeric,
    PrimaryGeneratedColumn,
    UpdateDateColumn,
)

from src.modules.holdings.entities.token_holding import TokenHolding
from src.modules.investors.entities.investor_profile import InvestorProfile

REDEMPTION_STATUSES = (
    "REQUESTED",
    "COMPLIANCE_APPROVED",
    "CUSTODIAN_RELEASED",
    "COMPLETED",
    "REJECTED",
    "CANCELLED",
)


@Entity()
class RedemptionRequest:
    id: int = PrimaryGeneratedColumn()
    investor: InvestorProfile = ManyToOne(lambda: InvestorProfile, inverse_side="redemption_requests", nullable=False)
    holding: TokenHolding = ManyToOne(lambda: TokenHolding, inverse_side="redemption_requests", nullable=False)

    units_requested: float = Column(type_=Numeric(precision=28, scale=8))

    # Populated by `RedemptionsService.approve` -- both `None` until then. See this module's
    # docstring for why the NAV snapshot happens at approval rather than request or completion.
    nav_per_unit_snapshot: float = Column(type_=Numeric(precision=18, scale=2), nullable=True)
    payout_amount: float = Column(type_=Numeric(precision=18, scale=2), nullable=True)

    status: str = Column(type_=EnumType(values=REDEMPTION_STATUSES), default="REQUESTED")

    rejection_reason: str = Column(nullable=True)

    # Populated at `COMPLETED` -- links this request to the `PayoutInstruction`/`LedgerEntry` pair
    # `RedemptionsService.complete` produces via `LedgerService.debit_payout_within`. Nullable
    # until then, mirrors `RedemptionRequest`'s own NAV-snapshot fields' nullable-until-transition
    # convention.
    payout_instruction_id: int = Column(nullable=True)

    # Single reused field for whichever officer/ops user last drove a state transition -- mirrors
    # `TokenizationProposal.reviewed_by_user_id`/`Subscription.processed_by_user_id`'s identical
    # single-field-reused-across-steps convention rather than one column per step.
    processed_by_user_id: int = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
