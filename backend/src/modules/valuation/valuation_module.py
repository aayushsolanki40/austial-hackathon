from austial import Module
from austial.orm import OrmModule, repository_token
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.issuance.issuance_module import IssuanceModule
from src.modules.valuation.entities.valuation_feed import ValuationFeed
from src.modules.valuation.valuation_controller import ValuationController
from src.modules.valuation.valuation_service import ValuationService


@Module(
    imports=[OrmModule.for_feature([ValuationFeed]), IssuanceModule],
    controllers=[ValuationController],
    providers=[ValuationService, JwtAuthGuard, RolesGuard],
    exports=[repository_token(ValuationFeed), ValuationService],
)
class ValuationModule:
    pass
