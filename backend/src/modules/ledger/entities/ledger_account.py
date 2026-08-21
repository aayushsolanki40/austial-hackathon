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

# IFSCA "freely convertible currency" set this platform actually supports today -- deliberately
# excludes INR, see this module's docstring. Extend as real banking-partner FCY corridors are
# added; this is not meant to be the exhaustive FATF/RBI freely-convertible-currency list.
FREELY_CONVERTIBLE_CURRENCIES = ("USD", "EUR", "GBP", "SGD", "AED", "AUD", "CAD", "JPY", "CHF")


@Entity()
class LedgerAccount:
    id: int = PrimaryGeneratedColumn()
    investor: InvestorProfile = ManyToOne(lambda: InvestorProfile, inverse_side="ledger_account", nullable=False)

    currency: str = Column(type_=EnumType(values=FREELY_CONVERTIBLE_CURRENCIES), default="USD")
    available_balance: float = Column(type_=Numeric(precision=18, scale=2), default=0)
    locked_balance: float = Column(type_=Numeric(precision=18, scale=2), default=0)

    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
