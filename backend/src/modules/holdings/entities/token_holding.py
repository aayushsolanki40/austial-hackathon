"""``TokenHolding`` entity -- Phase 6.

Created by ``SubscriptionsService.allocate`` (see that method's docstring) the moment a
``Subscription`` reaches ``ALLOCATED`` -- this row is the investor-visible "I own N units of this
series" record that closes the MVP loop (discover -> subscribe -> allocate -> hold).

★ REGULATORY: ownership is identity-keyed, NOT wallet-keyed -- ``investor`` is a ``ManyToOne``
straight to ``InvestorProfile``, never to a chain address. This mirrors ``WalletMapping``'s "PII
never co-located with chain addresses" rule from the other direction: a wallet address is never
even a candidate join key for "who owns this holding". Exactly the plan's own worked example --
this entity is written to match ``AUSTIAL_BUILD_PLAN.md``'s ``src/modules/holdings/entities/
token_holding.py`` code sketch field-for-field.

**One holding row per (investor, token_series)**, not one row per subscription -- a second
subscription against a series an investor already holds tops up ``quantity`` and recomputes a
quantity-weighted ``avg_cost_usd`` rather than inserting a duplicate row (see
``SubscriptionsService._upsert_holding``). ``status`` transitions (``ACTIVE`` -> ``FROZEN`` ->
``REDEEMED``) are Phase 7's redemption/freeze workflow -- out of scope here, this entity just
carries the column.

Not ``append_only`` -- unlike ``LedgerEntry``/``AuditLog``, ``status``/``quantity``/
``avg_cost_usd`` are expected to change in place over a holding's life (top-up allocations now,
freeze/redemption later). The generic ``AuditInterceptor`` already writes an ``AuditLog`` row on
every mutating request that touches this table, so a dedicated append-only ledger for
holdings-history is not duplicated here -- see this phase's task brief for that same reasoning.
"""

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
from src.modules.issuance.entities.token_series import TokenSeries

HOLDING_STATUSES = ("ACTIVE", "FROZEN", "REDEEMED")


@Entity()
class TokenHolding:
    id: int = PrimaryGeneratedColumn()

    # ★ REGULATORY: ownership is identity-keyed, NOT wallet-keyed.
    investor: InvestorProfile = ManyToOne(lambda: InvestorProfile, inverse_side="holdings", nullable=False)
    token_series: TokenSeries = ManyToOne(lambda: TokenSeries, inverse_side="holdings", nullable=False)

    quantity: float = Column(type_=Numeric(precision=28, scale=8))
    avg_cost_usd: float = Column(type_=Numeric(precision=18, scale=2))
    status: str = Column(type_=EnumType(values=HOLDING_STATUSES), default="ACTIVE")

    custodian_confirmation_ref: str = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
