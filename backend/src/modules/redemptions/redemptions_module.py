from austial import Module
from austial.orm import OrmModule

from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.kyc_verified_guard import KycVerifiedGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.holdings.holdings_module import HoldingsModule
from src.modules.investors.investors_module import InvestorsModule
from src.modules.issuance.issuance_module import IssuanceModule
from src.modules.ledger.ledger_module import LedgerModule
from src.modules.redemptions.entities.distribution import Distribution
from src.modules.redemptions.entities.redemption_request import RedemptionRequest
from src.modules.redemptions.redemptions_controller import RedemptionsController
from src.modules.redemptions.redemptions_service import RedemptionsService
from src.modules.valuation.valuation_module import ValuationModule


@Module(
    imports=[
        OrmModule.for_feature([RedemptionRequest, Distribution]),
        InvestorsModule,
        HoldingsModule,
        IssuanceModule,
        LedgerModule,
        ValuationModule,
    ],
    controllers=[RedemptionsController],
    providers=[RedemptionsService, JwtAuthGuard, RolesGuard, KycVerifiedGuard],
)
class RedemptionsModule:
    pass
