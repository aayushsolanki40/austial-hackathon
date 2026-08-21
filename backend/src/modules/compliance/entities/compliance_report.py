"""``ComplianceReport`` entity -- Phase 8.

IFSCA quarterly/annual compliance reports. Aggregates from ``TokenHolding`` (AUM via sum),
``InvestorProfile`` (investor count), ``TokenSeries`` (active issuances), ``LedgerEntry``
(currency breakdown). PDF rendered asynchronously via Celery task, uploaded to S3, key stored
in ``file_storage_key``.

Depends on Phase 1.0(b)'s ORM aggregation extensions (``.sum()``, ``.count()``) -- no raw SQL.
"""

from __future__ import annotations

from datetime import date, datetime

from austial.orm import Column, CreateDateColumn, Entity, EnumType, JSONType, Numeric, PrimaryGeneratedColumn

REPORT_TYPES = ("QUARTERLY_IFSCA", "ANNUAL_FINANCIALS")
REPORT_STATUSES = ("DRAFT", "FINALIZED")


@Entity()
class ComplianceReport:
    id: int = PrimaryGeneratedColumn()

    report_type: str = Column(type_=EnumType(values=REPORT_TYPES))
    period_start: date = Column()
    period_end: date = Column()

    generated_at: datetime = CreateDateColumn()
    generated_by_user_id: int = Column()

    # Aggregated metrics snapshot -- computed at report generation time, not live lookups.
    aum_total_usd: float = Column(type_=Numeric(precision=18, scale=2))
    investor_count: int = Column()
    active_issuances_count: int = Column()

    # Currency breakdown: dict of currency code -> total amount (e.g. {"USD": "1000000.00", "EUR": "500000.00"}).
    # Only freely-convertible currencies -- INR rejected at DTO layer.
    currency_breakdown: dict = Column(type_=JSONType())

    # S3 key for the rendered PDF (e.g. "compliance-reports/2026-Q3-quarterly-12345.pdf").
    file_storage_key: str = Column(nullable=True)

    status: str = Column(type_=EnumType(values=REPORT_STATUSES), default="DRAFT")
