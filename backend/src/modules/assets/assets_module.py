"""``AssetsModule`` -- Phase 3. Registers the ``Asset`` repository and the
``AssetsController``/``AssetsService`` pair. Explicitly imports ``IssuersModule`` and
``CustodiansModule`` (not just relying on the flat DI container -- see both those modules'
``exports=[repository_token(...)]`` docstrings) since ``AssetsService`` reads both the ``Issuer``
and ``Custodian`` repositories directly: the former to resolve "the issuer profile owning the
current user", the latter to enforce the ★ custodian-verification gate in ``attach_custodian``.
"""

from austial import Module
from austial.orm import OrmModule, repository_token

from src.modules.assets.assets_controller import AssetsController
from src.modules.assets.assets_service import AssetsService
from src.modules.assets.entities.asset import Asset
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.custodians.custodians_module import CustodiansModule
from src.modules.issuers.issuers_module import IssuersModule


@Module(
    imports=[OrmModule.for_feature([Asset]), IssuersModule, CustodiansModule],
    controllers=[AssetsController],
    providers=[AssetsService, JwtAuthGuard, RolesGuard],
    exports=[repository_token(Asset)],
)
class AssetsModule:
    pass
