"""``AmlScoringService`` -- Phase 9. XGBoost-based transaction risk scoring.

Integration point: Phase 8's ``ComplianceService.create_aml_alert()`` calls
``score_transaction()`` to populate ``AmlAlert.ml_model_version`` + ``risk_score``.

Model trained on synthetic data for demo (see ``ml/scripts/train_aml_model.py``).
Production deployment should retrain on real historical data + sanctions lists.

Features used:
- amount_usd: transaction amount normalized
- hour_of_day: 0-23
- days_since_last_tx: velocity indicator
- jurisdiction_risk_tier: 1-5 (higher = riskier)
- past_alert_count: cumulative count of past AML alerts for this entity
"""

from __future__ import annotations

import os
from typing import Any

import joblib
from austial.common import Injectable
from austial.orm import InjectRepository, Repository

from src.modules.ml.entities.ml_prediction import MlPrediction


@Injectable()
class AmlScoringService:
    def __init__(
        self,
        ml_prediction_repo: Repository[MlPrediction] = InjectRepository(MlPrediction),
    ):
        self.ml_prediction_repo = ml_prediction_repo
        self.model_path = os.path.join(os.path.dirname(__file__), "../scripts/aml_model.pkl")
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """Load XGBoost model from disk. If not found, fall back to heuristic scoring."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
        except Exception:
            self.model = None

    async def score_transaction(
        self,
        transaction_data: dict[str, Any],
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> dict[str, Any]:
        """Score transaction for AML risk.

        Args:
            transaction_data: dict with keys:
                - amount_usd: float
                - hour_of_day: int (0-23)
                - days_since_last_tx: int
                - jurisdiction_risk_tier: int (1-5)
                - past_alert_count: int
            entity_type: optional entity (e.g., "LedgerEntry")
            entity_id: optional entity ID

        Returns:
            Dict with risk_score (0-100), risk_level (LOW/MEDIUM/HIGH/CRITICAL)
        """
        try:
            features = self._extract_features(transaction_data)

            if self.model is not None:
                risk_score = self._score_with_model(features)
            else:
                risk_score = self._score_heuristic(features)

            risk_level = self._categorize_risk(risk_score)

            result = {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "features_used": features,
            }

            await self._log_prediction(
                model_name="aml_scoring",
                model_version="xgboost_v1.0" if self.model else "heuristic_v1.0",
                input_features=transaction_data,
                prediction_output=result,
                confidence_score=risk_score / 100.0,
                entity_type=entity_type,
                entity_id=entity_id,
            )

            return result

        except Exception as e:
            await self._log_prediction(
                model_name="aml_scoring",
                model_version="xgboost_v1.0" if self.model else "heuristic_v1.0",
                input_features=transaction_data,
                prediction_output={"error": str(e)},
                confidence_score=0.0,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            raise

    def _extract_features(self, data: dict[str, Any]) -> list[float]:
        """Extract feature vector for model."""
        return [
            float(data.get("amount_usd", 0)),
            float(data.get("hour_of_day", 12)),
            float(data.get("days_since_last_tx", 30)),
            float(data.get("jurisdiction_risk_tier", 1)),
            float(data.get("past_alert_count", 0)),
        ]

    def _score_with_model(self, features: list[float]) -> float:
        """Score using trained XGBoost model."""
        import numpy as np

        features_array = np.array(features).reshape(1, -1)
        prediction = self.model.predict_proba(features_array)[0]
        risk_score = prediction[1] * 100
        return float(risk_score)

    def _score_heuristic(self, features: list[float]) -> float:
        """Fallback heuristic scoring if model not available."""
        amount_usd, hour_of_day, days_since_last_tx, jurisdiction_risk_tier, past_alert_count = features

        score = 0.0

        if amount_usd > 100000:
            score += 30
        elif amount_usd > 50000:
            score += 20
        elif amount_usd > 10000:
            score += 10

        if hour_of_day < 6 or hour_of_day > 22:
            score += 15

        if days_since_last_tx < 1:
            score += 20
        elif days_since_last_tx < 7:
            score += 10

        score += jurisdiction_risk_tier * 5

        score += past_alert_count * 10

        return min(score, 100)

    def _categorize_risk(self, risk_score: float) -> str:
        """Categorize risk score into levels."""
        if risk_score >= 75:
            return "CRITICAL"
        elif risk_score >= 50:
            return "HIGH"
        elif risk_score >= 25:
            return "MEDIUM"
        else:
            return "LOW"

    async def _log_prediction(
        self,
        model_name: str,
        model_version: str,
        input_features: dict[str, Any],
        prediction_output: dict[str, Any],
        confidence_score: float | None,
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> None:
        """Internal helper: log every prediction to MlPrediction table."""
        prediction = MlPrediction()
        prediction.model_name = model_name
        prediction.model_version = model_version
        prediction.input_features = input_features
        prediction.prediction_output = prediction_output
        prediction.confidence_score = confidence_score
        prediction.entity_type = entity_type
        prediction.entity_id = entity_id

        await self.ml_prediction_repo.save(prediction)
