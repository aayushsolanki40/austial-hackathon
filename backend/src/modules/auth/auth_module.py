from austial import Module
from austial.orm import OrmModule

from src.modules.auth.auth_controller import AuthController
from src.modules.auth.auth_service import AuthService
from src.modules.auth.entities.refresh_token import RefreshToken
from src.modules.auth.entities.user import User
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.kyc_verified_guard import KycVerifiedGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.investors.investors_module import InvestorsModule


@Module(
    # `InvestorsModule` is imported here (rather than reaching for
    # `InvestorProfile` directly) purely for `KycVerifiedGuard`'s repository
    # injection -- it owns the entity, `auth` just consumes it.
    imports=[OrmModule.for_feature([User, RefreshToken]), InvestorsModule],
    controllers=[AuthController],
    providers=[AuthService, JwtAuthGuard, RolesGuard, KycVerifiedGuard],
    exports=[AuthService],
)
class AuthModule:
    pass
