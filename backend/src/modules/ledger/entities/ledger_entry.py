from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, EnumType, ManyToOne, Numeric, PrimaryGeneratedColumn

from src.modules.ledger.entities.ledger_account import FREELY_CONVERTIBLE_CURRENCIES, LedgerAccount

LEDGER_ENTRY_TYPES = (
    "CREDIT_FUNDING",
    "DEBIT_PAYOUT",
    "DEBIT_SUBSCRIPTION_SETTLEMENT",
    "CREDIT_REDEMPTION",
    "CREDIT_DISTRIBUTION",
)

# What kind of record `reference_id` points at -- there is no polymorphic FK in `austial.orm`
# (mirrors `AuditLog.entity_type`'s identical plain-string-tag pattern for the same reason).
LEDGER_ENTRY_REFERENCE_TYPES = (
    "FUNDING_INSTRUCTION",
    "PAYOUT_INSTRUCTION",
    "SUBSCRIPTION",
    "REDEMPTION",
    "DISTRIBUTION",
)


@Entity(append_only=True)
class LedgerEntry:
    id: int = PrimaryGeneratedColumn()
    account: LedgerAccount = ManyToOne(lambda: LedgerAccount, inverse_side="entries", nullable=False)

    entry_type: str = Column(type_=EnumType(values=LEDGER_ENTRY_TYPES))
    amount: float = Column(type_=Numeric(precision=18, scale=2))
    currency: str = Column(type_=EnumType(values=FREELY_CONVERTIBLE_CURRENCIES), default="USD")
    balance_after: float = Column(type_=Numeric(precision=18, scale=2))

    reference_type: str = Column(type_=EnumType(values=LEDGER_ENTRY_REFERENCE_TYPES))
    reference_id: int = Column(nullable=True)

    idempotency_key: str = Column(unique=True)

    created_at: datetime = CreateDateColumn()
