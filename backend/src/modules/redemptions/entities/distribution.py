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

from src.modules.issuance.entities.token_series import TokenSeries
from src.modules.ledger.entities.ledger_account import FREELY_CONVERTIBLE_CURRENCIES

DISTRIBUTION_STATUSES = ("DRAFT", "PROCESSING", "COMPLETED")


@Entity()
class Distribution:
    id: int = PrimaryGeneratedColumn()
    token_series: TokenSeries = ManyToOne(lambda: TokenSeries, inverse_side="distributions", nullable=False)

    total_amount: float = Column(type_=Numeric(precision=18, scale=2))
    currency: str = Column(type_=EnumType(values=FREELY_CONVERTIBLE_CURRENCIES), default="USD")

    # The as-of date this distribution is declared for -- distinct from `created_at`
    # (when the row was drafted) and `processed_at` (when it was actually paid out). Mirrors
    # `ValuationFeed.reported_at`'s identical "declared-as-of vs. ingested/processed-at" split.
    record_date: datetime = Column(type_=DateTime())

    status: str = Column(type_=EnumType(values=DISTRIBUTION_STATUSES), default="DRAFT")

    triggered_by_user_id: int = Column(nullable=True)
    processed_at: datetime = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
    updated_at: datetime = UpdateDateColumn()
