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

from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.ledger.entities.ledger_account import FREELY_CONVERTIBLE_CURRENCIES

FUNDING_INSTRUCTION_STATUSES = ("PENDING", "CONFIRMED", "EXPIRED")


@Entity()
class FundingInstruction:
    id: int = PrimaryGeneratedColumn()
    investor: InvestorProfile = ManyToOne(
        lambda: InvestorProfile, inverse_side="funding_instructions", nullable=False
    )

    # Investor-supplied bank-transfer memo/reference -- the only thing a real banking-partner
    # webhook or an ops officer reconciling a bank statement would have to match this row against.
    reference_code: str = Column(unique=True)

    amount: float = Column(type_=Numeric(precision=18, scale=2))
    currency: str = Column(type_=EnumType(values=FREELY_CONVERTIBLE_CURRENCIES), default="USD")
    status: str = Column(type_=EnumType(values=FUNDING_INSTRUCTION_STATUSES), default="PENDING")

    expires_at: datetime = Column(nullable=True)
    confirmed_by_user_id: int = Column(nullable=True)
    confirmed_at: datetime = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
