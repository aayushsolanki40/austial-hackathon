"""``ValuationAnomalyService`` -- Phase 9. Statistical anomaly detection for valuation feeds.

Integration point: Phase 7's ``ValuationService`` calls ``detect_anomaly()``
before publishing a new valuation feed. If anomaly_score > 0.8, the feed is
quarantined instead of published.

Uses z-score and IQR methods for simple but effective outlier detection.
Production deployment could enhance with Prophet or LSTM for time-series
anomaly detection.
"""

from __future__ import annotations

from typing import Any

from austial.common import Injectable
from austial.orm import InjectRepository, Repository

from src.modules.ml.entities.ml_prediction import MlPrediction


@Injectable()
class ValuationAnomalyService:
    def __init__(
        self,
        ml_prediction_repo: Repository[MlPrediction] = InjectRepository(MlPrediction),
    ):
        self.ml_prediction_repo = ml_prediction_repo

    async def detect_anomaly(
        self,
        feed_id: int,
        new_price: float,
        trailing_prices: list[float],
    ) -> dict[str, Any]:
        """Detect if new price is anomalous compared to trailing history.

        Args:
            feed_id: ValuationFeed ID for audit logging
            new_price: New price to evaluate
            trailing_prices: Historical prices (last N observations)

        Returns:
            Dict with anomaly_score (0-1), is_anomaly (bool), method used, details
        """
        try:
            if len(trailing_prices) < 3:
                result = {
                    "anomaly_score": 0.0,
                    "is_anomaly": False,
                    "reason": "insufficient_history",
                    "trailing_count": len(trailing_prices),
                }
            else:
                z_score_result = self._z_score_anomaly(new_price, trailing_prices)
                iqr_result = self._iqr_anomaly(new_price, trailing_prices)

                anomaly_score = max(z_score_result["score"], iqr_result["score"])
                is_anomaly = anomaly_score > 0.8

                result = {
                    "anomaly_score": anomaly_score,
                    "is_anomaly": is_anomaly,
                    "z_score": z_score_result,
                    "iqr": iqr_result,
                    "trailing_count": len(trailing_prices),
                }

            await self._log_prediction(
                model_name="valuation_anomaly",
                model_version="zscore_iqr_v1.0",
                input_features={
                    "feed_id": feed_id,
                    "new_price": new_price,
                    "trailing_prices": trailing_prices,
                },
                prediction_output=result,
                confidence_score=result["anomaly_score"],
                entity_type="ValuationFeed",
                entity_id=feed_id,
            )

            return result

        except Exception as e:
            await self._log_prediction(
                model_name="valuation_anomaly",
                model_version="zscore_iqr_v1.0",
                input_features={
                    "feed_id": feed_id,
                    "new_price": new_price,
                    "trailing_prices": trailing_prices,
                },
                prediction_output={"error": str(e)},
                confidence_score=0.0,
                entity_type="ValuationFeed",
                entity_id=feed_id,
            )
            raise

    def _z_score_anomaly(self, new_price: float, trailing_prices: list[float]) -> dict[str, Any]:
        """Z-score based anomaly detection."""
        import statistics

        mean = statistics.mean(trailing_prices)
        stdev = statistics.stdev(trailing_prices) if len(trailing_prices) > 1 else 0.0

        if stdev == 0:
            return {"score": 0.0, "z_score": 0.0, "mean": mean, "stdev": stdev}

        z_score = abs((new_price - mean) / stdev)

        anomaly_score = min(z_score / 3.0, 1.0)

        return {
            "score": anomaly_score,
            "z_score": z_score,
            "mean": mean,
            "stdev": stdev,
        }

    def _iqr_anomaly(self, new_price: float, trailing_prices: list[float]) -> dict[str, Any]:
        """IQR-based anomaly detection."""
        import statistics

        sorted_prices = sorted(trailing_prices)
        q1 = statistics.median(sorted_prices[: len(sorted_prices) // 2])
        q3 = statistics.median(sorted_prices[len(sorted_prices) // 2 :])
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        is_outlier = new_price < lower_bound or new_price > upper_bound

        if is_outlier:
            distance_from_bound = max(lower_bound - new_price, new_price - upper_bound, 0)
            anomaly_score = min(distance_from_bound / iqr if iqr > 0 else 1.0, 1.0)
        else:
            anomaly_score = 0.0

        return {
            "score": anomaly_score,
            "is_outlier": is_outlier,
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
        }

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
