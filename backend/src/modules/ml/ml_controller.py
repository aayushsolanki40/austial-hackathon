"""``MlController`` -- Phase 9. Admin endpoints for ML model monitoring.

All endpoints guarded by ``RolesGuard(['ADMIN'])`` -- ML model introspection
is sensitive operational data, not public API.
"""

from __future__ import annotations

from typing import Any

from austial.common import Controller, Get, Query, UseGuards
from austial.orm import InjectRepository, Repository

from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.ml.entities.ml_prediction import MlPrediction


@Controller("ml")
@UseGuards(JwtAuthGuard, RolesGuard)
@Roles("ADMIN")
class MlController:
    def __init__(
        self,
        ml_prediction_repo: Repository[MlPrediction] = InjectRepository(MlPrediction),
    ):
        self.ml_prediction_repo = ml_prediction_repo

    @Get("models")
    async def list_models(self) -> dict[str, Any]:
        """List all ML models with their versions and usage statistics.

        Returns:
            Dict with models array containing model_name, version, prediction_count, last_used
        """
        results = await self.ml_prediction_repo.find()

        models_map: dict[str, dict[str, Any]] = {}

        for prediction in results:
            key = f"{prediction.model_name}:{prediction.model_version}"
            if key not in models_map:
                models_map[key] = {
                    "model_name": prediction.model_name,
                    "model_version": prediction.model_version,
                    "prediction_count": 0,
                    "last_used": prediction.predicted_at,
                    "first_used": prediction.predicted_at,
                }

            models_map[key]["prediction_count"] += 1
            if prediction.predicted_at > models_map[key]["last_used"]:
                models_map[key]["last_used"] = prediction.predicted_at

        models_list = sorted(models_map.values(), key=lambda x: x["last_used"], reverse=True)

        return {
            "models": models_list,
            "total_models": len(models_list),
        }

    @Get("predictions")
    async def list_predictions(
        self,
        model_name: str | None = Query(default=None),
        entity_type: str | None = Query(default=None),
        limit: int = Query(default=100),
    ) -> dict[str, Any]:
        """Query ML predictions for debugging/audit.

        Query params:
            model_name: Filter by model name (optional)
            entity_type: Filter by entity type (optional)
            limit: Max results (default 100)

        Returns:
            Dict with predictions array and metadata
        """
        filters = {}
        if model_name:
            filters["model_name"] = model_name
        if entity_type:
            filters["entity_type"] = entity_type

        if filters:
            predictions = await self.ml_prediction_repo.find_by(filters)
        else:
            predictions = await self.ml_prediction_repo.find()

        predictions = predictions[:limit]

        predictions_data = [
            {
                "id": p.id,
                "model_name": p.model_name,
                "model_version": p.model_version,
                "confidence_score": float(p.confidence_score) if p.confidence_score else None,
                "entity_type": p.entity_type,
                "entity_id": p.entity_id,
                "predicted_at": p.predicted_at.isoformat(),
                "input_features": p.input_features,
                "prediction_output": p.prediction_output,
            }
            for p in predictions
        ]

        return {
            "predictions": predictions_data,
            "count": len(predictions_data),
            "filters_applied": filters,
        }
