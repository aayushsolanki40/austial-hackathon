from austial import Module
from austial.orm import OrmModule, repository_token

from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.holdings.entities.token_holding import TokenHolding
from src.modules.holdings.holdings_controller import HoldingsController
from src.modules.holdings.holdings_service import HoldingsService
from src.modules.investors.investors_module import InvestorsModule


@Module(
    imports=[OrmModule.for_feature([TokenHolding]), InvestorsModule],
    controllers=[HoldingsController],
    providers=[HoldingsService, JwtAuthGuard, RolesGuard],
    exports=[repository_token(TokenHolding)],
)
class HoldingsModule:
    pass
