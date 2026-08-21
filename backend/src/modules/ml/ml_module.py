"""``MlModule`` -- Phase 9. Machine learning services and model monitoring."""

from austial import Module
from austial.orm import OrmModule

from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.issuers.entities.issuer import Issuer
from src.modules.ml.entities.ml_prediction import MlPrediction
from src.modules.ml.ml_controller import MlController
from src.modules.ml.services.aml_scoring_service import AmlScoringService
from src.modules.ml.services.contract_risk_service import ContractRiskService
from src.modules.ml.services.issuer_trust_service import IssuerTrustService
from src.modules.ml.services.kyc_ml_service import KycMlService
from src.modules.ml.services.valuation_anomaly_service import ValuationAnomalyService


@Module(
    imports=[
        OrmModule.for_feature([MlPrediction, Issuer]),
    ],
    controllers=[MlController],
    providers=[
        KycMlService,
        AmlScoringService,
        ValuationAnomalyService,
        ContractRiskService,
        IssuerTrustService,
        JwtAuthGuard,
        RolesGuard,
    ],
    exports=[
        KycMlService,
        AmlScoringService,
        ValuationAnomalyService,
        ContractRiskService,
        IssuerTrustService,
    ],
)
class MlModule:
    pass
