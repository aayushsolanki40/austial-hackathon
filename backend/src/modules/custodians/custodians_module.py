"""``CustodiansModule`` -- Phase 3. Registers the ``Custodian`` repository and the
``CustodiansController``/``CustodiansService`` pair. ``exports=[repository_token(Custodian)]``
kept for ``AssetsModule``, whose ``AssetsService`` needs direct ``Custodian`` repository access
to check ``ifsca_verified`` before attaching a custodian to an ``Asset`` -- mirrors
``InvestorsModule``'s identical export for ``KycVerifiedGuard``.
"""

from austial import Module
from austial.orm import OrmModule, repository_token

from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.custodians.custodians_controller import CustodiansController
from src.modules.custodians.custodians_service import CustodiansService
from src.modules.custodians.entities.custodian import Custodian


@Module(
    imports=[OrmModule.for_feature([Custodian])],
    controllers=[CustodiansController],
    providers=[CustodiansService, JwtAuthGuard, RolesGuard],
    exports=[repository_token(Custodian)],
)
class CustodiansModule:
    pass
