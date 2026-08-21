"""``MlPrediction`` entity -- Phase 9. APPEND-ONLY audit trail for all ML predictions.

Every model prediction (KYC OCR, AML scoring, valuation anomaly detection, etc.)
logs to this table before returning. Regulatory justification: every automated
decision must be explainable and auditable — inputs + outputs + model version
retained for 7 years (IFSCA requirement).

No ``UPDATE``/``DELETE`` code path may ever be added for this entity -- same
append-only discipline as ``AuditLog`` (see that entity's docstring). Enforced
at the framework level via ``@Entity(append_only=True)`` -- ``EntityManager``
raises ``AppendOnlyViolationError`` on any update/delete operation.

Usage pattern: every ML service method calls ``Repository.save()`` with a fresh
``MlPrediction`` row before returning its prediction to the caller.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from austial.orm import Column, CreateDateColumn, Entity, JSONType, Numeric, PrimaryGeneratedColumn


@Entity(append_only=True)
class MlPrediction:
    id: int = PrimaryGeneratedColumn()

    model_name: str = Column()
    model_version: str = Column()

    input_features: dict[str, Any] = Column(type_=JSONType())
    prediction_output: dict[str, Any] = Column(type_=JSONType())

    confidence_score: Decimal | None = Column(type_=Numeric(5, 4), nullable=True)

    entity_type: str | None = Column(nullable=True)
    entity_id: int | None = Column(nullable=True)

    predicted_at: datetime = CreateDateColumn()
