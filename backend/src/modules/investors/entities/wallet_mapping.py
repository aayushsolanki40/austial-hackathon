"""``WalletMapping`` entity -- Phase 2.

★ REGULATORY RULE (see ``AUSTIAL_BUILD_PLAN.md`` Section 1's "PII never
co-located with chain addresses" instruction, repeated in Phase 2's scope):
a chain wallet address must never be stored as a column on ``InvestorProfile``
or ``User`` -- both of those carry (or are directly linked to) identity
data. This entity exists purely so a wallet address lives in its **own**
table, joined only by FK, so a database-level scope that only needs
addresses (e.g. an on-chain reconciliation job) never has to touch a table
that also carries PII.

Also reinforces the build plan's other non-negotiable modelling rule:
``TokenHolding`` (Phase 6) is keyed by ``investor_id``, never by wallet
address -- a ``WalletMapping`` row is a *reference* an investor has
associated with their identity-keyed profile, not an alternate primary key
for ownership.
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, EnumType, ManyToOne, PrimaryGeneratedColumn

from src.modules.investors.entities.investor_profile import InvestorProfile

# Kept as a small closed set of chains/networks this platform actually supports today, rather
# than free text -- extend as real DLT integrations land (see the build plan's note that the
# off-chain ledger stays authoritative and on-chain is execution-only).
WALLET_CHAINS = ("ETHEREUM", "POLYGON", "PERMISSIONED_DLT")

WALLET_STATUSES = ("ACTIVE", "REVOKED")


@Entity()
class WalletMapping:
    id: int = PrimaryGeneratedColumn()

    # Owning FK only -- no PII column lives on this table (see module docstring).
    investor: InvestorProfile = ManyToOne(lambda: InvestorProfile, inverse_side="wallet_mappings", nullable=False)

    chain: str = Column(type_=EnumType(values=WALLET_CHAINS))
    address: str = Column()
    label: str = Column(nullable=True)
    status: str = Column(type_=EnumType(values=WALLET_STATUSES), default="ACTIVE")

    created_at: datetime = CreateDateColumn()
