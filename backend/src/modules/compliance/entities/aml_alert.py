"""``AmlAlert`` entity -- Phase 8.

AML alert generation from rule-based scoring (Phase 8) with a pluggable seam for ML-based
scoring (Phase 9). Both ``rule_triggered`` (current) and ``ml_model_version`` (future) columns
exist from the start so the XGBoost model drops in without schema change.

★ Phase 9 integration point: when ``AmlAlertService.create_aml_alert()`` is extended to call the
XGBoost model (``GET /ml/predict-risk``), the returned risk score goes into ``risk_score`` and
the model version stamp goes into ``ml_model_version`` -- both columns are already here.
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, EnumType, ManyToOne, Numeric, PrimaryGeneratedColumn

from src.modules.auth.entities.user import User
from src.modules.investors.entities.investor_profile import InvestorProfile

ALERT_TYPES = (
    "LARGE_TRANSACTION",
    "RAPID_SUCCESSION",
    "HIGH_RISK_JURISDICTION",
    "SANCTIONS_MATCH",
    "ANOMALY",
)

ALERT_STATUSES = ("OPEN", "UNDER_REVIEW", "DISMISSED", "ESCALATED")


@Entity()
class AmlAlert:
    id: int = PrimaryGeneratedColumn()

    transaction_ref: str = Column()
    investor: InvestorProfile = ManyToOne(lambda: InvestorProfile, inverse_side="aml_alerts", nullable=False)

    alert_type: str = Column(type_=EnumType(values=ALERT_TYPES))
    risk_score: float = Column(type_=Numeric(precision=5, scale=2))
    status: str = Column(type_=EnumType(values=ALERT_STATUSES), default="OPEN")

    # Current rule-based triggering -- populated immediately in Phase 8.
    rule_triggered: str = Column(nullable=True)

    # Future ML model version stamp -- populated in Phase 9 when XGBoost integration lands.
    ml_model_version: str = Column(nullable=True)

    assigned_officer: User = ManyToOne(lambda: User, inverse_side="assigned_aml_alerts", nullable=True)
    resolution_notes: str = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
    resolved_at: datetime = Column(nullable=True)
