from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, EnumType, ManyToOne, Numeric, PrimaryGeneratedColumn

from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.ledger.entities.ledger_account import FREELY_CONVERTIBLE_CURRENCIES

PAYOUT_INSTRUCTION_STATUSES = ("RECORDED",)


@Entity()
class PayoutInstruction:
    id: int = PrimaryGeneratedColumn()
    investor: InvestorProfile = ManyToOne(lambda: InvestorProfile, inverse_side="payout_instructions", nullable=False)

    amount: float = Column(type_=Numeric(precision=18, scale=2))
    currency: str = Column(type_=EnumType(values=FREELY_CONVERTIBLE_CURRENCIES), default="USD")
    status: str = Column(type_=EnumType(values=PAYOUT_INSTRUCTION_STATUSES), default="RECORDED")

    memo: str = Column(nullable=True)
    recorded_by_user_id: int = Column(nullable=True)
    recorded_at: datetime = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
