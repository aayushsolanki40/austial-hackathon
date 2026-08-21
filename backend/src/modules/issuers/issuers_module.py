"""``IssuersModule`` -- Phase 3. Registers the ``Issuer`` repository and the
``IssuersController``/``IssuersService`` pair. ``exports=[repository_token(Issuer)]`` kept for
``AssetsModule``, whose ``AssetsService`` needs direct ``Issuer`` repository access to resolve
"the issuer profile owning the current user" -- mirrors ``InvestorsModule``'s identical export
for ``KycVerifiedGuard``.
"""

from austial import Module
from austial.orm import OrmModule, repository_token

from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.issuers.entities.issuer import Issuer
from src.modules.issuers.issuers_controller import IssuersController
from src.modules.issuers.issuers_service import IssuersService


@Module(
    imports=[OrmModule.for_feature([Issuer])],
    controllers=[IssuersController],
    providers=[IssuersService, JwtAuthGuard, RolesGuard],
    exports=[repository_token(Issuer)],
)
class IssuersModule:
    pass
