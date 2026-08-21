"""``ValuationFeed`` entity -- Phase 7.

One row per NAV report ingested for a ``TokenSeries``. ★ REGULATORY: ``status`` is decided at
insert time by ``ValuationService.submit_feed``'s anomaly-deviation check (see that method's
docstring) -- a feed that deviates too far from its series' recent trailing average is created as
``QUARANTINED`` directly, never briefly ``PUBLISHED`` then walked back. This is the backend half of
IFSCA's oracle-manipulation concern in the RWA consultation paper.

``reviewed_by_user_id``/``reviewed_at`` are populated only when a ``QUARANTINED`` feed is later
manually approved by a compliance officer (``ValuationService.approve_quarantined_feed``) -- both
stay ``None`` for a feed that was ``PUBLISHED`` outright at ingestion. Mirrors
``TokenizationProposal.reviewed_by_user_id``'s single-field-reused convention.

Money rule: ``nav_per_unit`` is ``Numeric``, never ``Float`` -- mirrors
``TokenizationProposal.unit_price_usd``. ``anomaly_score`` is a plain ``Float`` (a relative
deviation ratio, not a currency amount) and is nullable -- ``None`` for a series' very first feed,
which has no trailing history to compare against and is always published.
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import (
    Column,
    CreateDateColumn,
    DateTime,
    Entity,
    EnumType,
    Float,
    ManyToOne,
    Numeric,
    PrimaryGeneratedColumn,
)

from src.modules.issuance.entities.token_series import TokenSeries

VALUATION_FEED_STATUSES = ("PUBLISHED", "QUARANTINED")


@Entity()
class ValuationFeed:
    id: int = PrimaryGeneratedColumn()
    token_series: TokenSeries = ManyToOne(lambda: TokenSeries, inverse_side="valuation_feeds", nullable=False)

    nav_per_unit: float = Column(type_=Numeric(precision=18, scale=2))
    source: str = Column()
    anomaly_score: float = Column(type_=Float(), nullable=True)
    status: str = Column(type_=EnumType(values=VALUATION_FEED_STATUSES), default="PUBLISHED")

    # When the feed's source reports the NAV as of -- distinct from `created_at` (when it was
    # ingested into this system). NAV history is charted/ordered by this, not `created_at`.
    reported_at: datetime = Column(type_=DateTime())

    reviewed_by_user_id: int = Column(nullable=True)
    reviewed_at: datetime = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
