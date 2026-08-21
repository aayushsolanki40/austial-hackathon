"""Unit tests for ML services -- Phase 9."""

import pytest
from austial.orm import DataSource, OrmModule
from austial.testing import Test

from src.modules.ml.entities.ml_prediction import MlPrediction
from src.modules.ml.services.aml_scoring_service import AmlScoringService
from src.modules.ml.services.kyc_ml_service import KycMlService
from src.modules.ml.services.valuation_anomaly_service import ValuationAnomalyService


@pytest.fixture
async def module():
    """Create testing module with ML services."""
    testing_module = await Test.create_testing_module(
        imports=[
            OrmModule.for_root(
                type_="sqlite",
                url="sqlite+aiosqlite:///:memory:",
                entities=[MlPrediction],
                synchronize=True,
            ),
            OrmModule.for_feature([MlPrediction]),
        ],
        controllers=[],
        providers=[
            AmlScoringService,
            KycMlService,
            ValuationAnomalyService,
        ],
    ).compile()
    await testing_module.get(DataSource).initialize()
    return testing_module


@pytest.mark.asyncio
async def test_aml_scoring_service_heuristic(module):
    """Test AML scoring service with heuristic fallback."""
    aml_service = module.get(AmlScoringService)

    transaction_data = {
        "amount_usd": 150000,
        "hour_of_day": 2,
        "days_since_last_tx": 0.5,
        "jurisdiction_risk_tier": 5,
        "past_alert_count": 3,
    }

    result = await aml_service.score_transaction(transaction_data)

    assert "risk_score" in result
    assert "risk_level" in result
    assert result["risk_score"] >= 0
    assert result["risk_score"] <= 100
    assert result["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@pytest.mark.asyncio
async def test_valuation_anomaly_service_insufficient_history(module):
    """Test valuation anomaly detection with insufficient history."""
    valuation_service = module.get(ValuationAnomalyService)

    result = await valuation_service.detect_anomaly(
        feed_id=1,
        new_price=100.0,
        trailing_prices=[99.0],
    )

    assert result["is_anomaly"] is False
    assert result["reason"] == "insufficient_history"


@pytest.mark.asyncio
async def test_valuation_anomaly_service_outlier(module):
    """Test valuation anomaly detection with clear outlier."""
    valuation_service = module.get(ValuationAnomalyService)

    trailing_prices = [100.0, 101.0, 99.0, 100.5, 99.5] * 5
    new_price = 200.0

    result = await valuation_service.detect_anomaly(
        feed_id=1,
        new_price=new_price,
        trailing_prices=trailing_prices,
    )

    assert result["anomaly_score"] > 0.5
