"""``IssuerTrustService`` -- Phase 9. Issuer trustworthiness scoring.

Integration point: Phase 3's issuer review dashboard can surface this score
to help compliance officers prioritize reviews.

Heuristic scoring based on Issuer fields: IFSCA registration status, past
issuance history, rejection count, business age, etc. Production deployment
should enhance with external credit/reputation data.
"""

from __future__ import annotations

from typing import Any

from austial.common import Injectable
from austial.orm import InjectRepository, Repository

from src.modules.issuers.entities.issuer import Issuer
from src.modules.ml.entities.ml_prediction import MlPrediction


@Injectable()
class IssuerTrustService:
    def __init__(
        self,
        ml_prediction_repo: Repository[MlPrediction] = InjectRepository(MlPrediction),
        issuer_repo: Repository[Issuer] = InjectRepository(Issuer),
    ):
        self.ml_prediction_repo = ml_prediction_repo
        self.issuer_repo = issuer_repo

    async def score_issuer_trustworthiness(self, issuer_id: int) -> dict[str, Any]:
        """Score issuer trustworthiness.

        Args:
            issuer_id: Issuer entity ID

        Returns:
            Dict with trust_score (0-100), trust_level, factors breakdown
        """
        try:
            issuer = await self.issuer_repo.find_one_by({"id": issuer_id})
            if not issuer:
                raise ValueError(f"Issuer {issuer_id} not found")

            factors = []
            trust_score = 50.0

            if issuer.ifsca_registration_number:
                trust_score += 25
                factors.append({"factor": "ifsca_registered", "impact": +25, "description": "IFSCA registered"})
            else:
                trust_score -= 15
                factors.append({"factor": "not_ifsca_registered", "impact": -15, "description": "Not IFSCA registered"})

            if issuer.ifsca_license_status == "ACTIVE":
                trust_score += 15
                factors.append({"factor": "active_license", "impact": +15, "description": "Active IFSCA license"})
            elif issuer.ifsca_license_status == "SUSPENDED":
                trust_score -= 30
                factors.append({"factor": "suspended_license", "impact": -30, "description": "Suspended license"})

            issuer_age_score = self._calculate_age_score(issuer)
            trust_score += issuer_age_score
            factors.append(
                {
                    "factor": "business_age",
                    "impact": issuer_age_score,
                    "description": f"Business established {issuer.year_established or 'unknown'}",
                }
            )

            trust_score = max(0, min(trust_score, 100))
            trust_level = self._categorize_trust(trust_score)

            result = {
                "trust_score": trust_score,
                "trust_level": trust_level,
                "factors": factors,
                "issuer_name": issuer.legal_name,
            }

            await self._log_prediction(
                model_name="issuer_trust",
                model_version="heuristic_v1.0",
                input_features={
                    "issuer_id": issuer_id,
                    "has_ifsca_registration": issuer.ifsca_registration_number is not None,
                    "license_status": issuer.ifsca_license_status,
                    "year_established": issuer.year_established,
                },
                prediction_output=result,
                confidence_score=trust_score / 100.0,
                entity_type="Issuer",
                entity_id=issuer_id,
            )

            return result

        except Exception as e:
            await self._log_prediction(
                model_name="issuer_trust",
                model_version="heuristic_v1.0",
                input_features={"issuer_id": issuer_id},
                prediction_output={"error": str(e)},
                confidence_score=0.0,
                entity_type="Issuer",
                entity_id=issuer_id,
            )
            raise

    def _calculate_age_score(self, issuer: Issuer) -> float:
        """Calculate trust score contribution based on business age."""
        if not issuer.year_established:
            return -5

        from datetime import datetime

        current_year = datetime.now().year
        age = current_year - issuer.year_established

        if age >= 20:
            return 15
        elif age >= 10:
            return 10
        elif age >= 5:
            return 5
        elif age >= 2:
            return 0
        else:
            return -5

    def _categorize_trust(self, trust_score: float) -> str:
        """Categorize trust score into levels."""
        if trust_score >= 80:
            return "HIGH"
        elif trust_score >= 60:
            return "MEDIUM"
        elif trust_score >= 40:
            return "LOW"
        else:
            return "VERY_LOW"

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
