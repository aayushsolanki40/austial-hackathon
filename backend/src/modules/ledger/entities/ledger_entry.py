from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, EnumType, ManyToOne, Numeric, PrimaryGeneratedColumn

from src.modules.ledger.entities.ledger_account import FREELY_CONVERTIBLE_CURRENCIES, LedgerAccount

# `DEBIT_SUBSCRIPTION_SETTLEMENT` -- Phase 6, added by `LedgerService.settle_locked_funds`. Unlike
# `CREDIT_FUNDING`/`DEBIT_PAYOUT` (which move `available_balance`), this entry type records the
# *locked* portion of an account being consumed at allocation time (funds paid for a `TokenHolding`
# leave the ledger account entirely -- a genuine total-balance-affecting event). `balance_after` for
# this entry type is `locked_balance` after the debit, not `available_balance` -- see
# `LedgerService.settle_locked_funds`'s docstring. Deliberately excludes lock/unlock themselves --
# see `SubscriptionsService`'s and `LedgerService.lock_funds`'s docstrings for why those two do
# *not* get an entry (they only move funds between `available_balance`/`locked_balance`, the
# account's total balance is unchanged, so there is no balance-affecting event to record here).
LEDGER_ENTRY_TYPES = ("CREDIT_FUNDING", "DEBIT_PAYOUT", "DEBIT_SUBSCRIPTION_SETTLEMENT")

# What kind of record `reference_id` points at -- there is no polymorphic FK in `austial.orm`
# (mirrors `AuditLog.entity_type`'s identical plain-string-tag pattern for the same reason).
LEDGER_ENTRY_REFERENCE_TYPES = ("FUNDING_INSTRUCTION", "PAYOUT_INSTRUCTION", "SUBSCRIPTION")


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
