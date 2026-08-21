"""``Subscription`` entity -- Phase 6. Owns the state machine ``SubscriptionsService`` enforces::

    PENDING -> FUNDED -> CONFIRMED -> ALLOCATED
            \\-> CANCELLED (investor self-service, PENDING only)
    FUNDED, CONFIRMED -> REFUNDED (officer-driven reversal, pre-allocation)

The build plan's own ASCII diagram draws ``REFUNDED``/``CANCELLED`` branching off ``PENDING``
alone -- that is the common case and is exactly what this entity's docstring/``SubscriptionsService.
ALLOWED_TRANSITIONS`` implement for ``CANCELLED`` (investor-initiated, ``PENDING`` only, per the
plan's explicit "cancel my own PENDING subscription" endpoint). ``REFUNDED`` is additionally
reachable from ``FUNDED``/``CONFIRMED`` -- a deliberate, documented superset of the diagram's
literal reading: without it, a ``CONFIRMED`` subscription that misses out on allocation (the
token series' remaining supply is already exhausted by an earlier allocation round, see
``SubscriptionsService.allocate``) would have no legal exit from the state machine at all. See
``SubscriptionsService``'s module docstring for the full reasoning.

``units`` requested at subscribe time vs. ``allocated_units`` actually granted (nullable until
``ALLOCATED``) differ under oversubscription -- ``SubscriptionsService.allocate`` pro-rates,
so ``allocated_units <= units`` always holds once set. Money rule: ``Numeric``, never ``Float`` --
mirrors ``TokenizationProposal``/``LedgerAccount``.
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

SUBSCRIPTION_STATUSES = ("PENDING", "FUNDED", "CONFIRMED", "ALLOCATED", "REFUNDED", "CANCELLED")


@Entity()
class Subscription:
    id: int = PrimaryGeneratedColumn()
    investor: InvestorProfile = ManyToOne(lambda: InvestorProfile, inverse_side="subscriptions", nullable=False)
    token_series: TokenSeries = ManyToOne(lambda: TokenSeries, inverse_side="subscriptions", nullable=False)

    # Requested at subscribe time -- `amount_usd` is a snapshot of `units * proposal.unit_price_usd`
    # at that instant (mirrors `TokenSeries.total_supply`'s "snapshot, not a live read" convention),
    # since `proposal.unit_price_usd` has no later mutation path today but a subscription's own
    # economics must never silently drift if it ever did.
    units: float = Column(type_=Numeric(precision=28, scale=8))
    amount_usd: float = Column(type_=Numeric(precision=18, scale=2))

    # Populated by `SubscriptionsService.allocate` -- `None` until `ALLOCATED`. See this module's
    # docstring on why this can be `< units` under pro-rata oversubscription.
    allocated_units: float = Column(type_=Numeric(precision=28, scale=8), nullable=True)

    status: str = Column(type_=EnumType(values=SUBSCRIPTION_STATUSES), default="PENDING")

    # Single reused field for whichever officer last drove a `FUNDED`/`CONFIRMED`/`REFUNDED`
    # transition -- mirrors `TokenizationProposal.reviewed_by_user_id`'s identical
    # single-field-reused-across-steps convention rather than one column per step.
    processed_by_user_id: int = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
