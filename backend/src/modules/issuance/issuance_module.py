"""``IssuanceModule`` -- Phase 4. Registers the four Phase-4 entity repositories and the
``IssuanceController``/``IssuanceService`` pair. Explicitly imports ``AssetsModule`` and
``IssuersModule`` (not just relying on the flat DI container -- see both those modules'
``exports=[repository_token(...)]`` docstrings) since ``IssuanceService`` reads the ``Asset``
repository directly (to resolve/re-check the ★ tokenization-readiness gate) and the ``Issuer``
repository directly (to resolve "the issuer profile owning the current user", mirroring
``AssetsService``/``KycService``).
"""

from austial import Module
from austial.orm import OrmModule, repository_token

from src.modules.assets.assets_module import AssetsModule
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.issuance.entities.disclosure_document import DisclosureDocument
from src.modules.issuance.entities.smart_contract_deployment import SmartContractDeployment
from src.modules.issuance.entities.token_series import TokenSeries
from src.modules.issuance.entities.tokenization_proposal import TokenizationProposal
from src.modules.issuance.issuance_controller import IssuanceController
from src.modules.issuance.issuance_service import IssuanceService
from src.modules.issuers.issuers_module import IssuersModule


@Module(
    imports=[
        OrmModule.for_feature([TokenizationProposal, DisclosureDocument, TokenSeries, SmartContractDeployment]),
        AssetsModule,
        IssuersModule,
    ],
    controllers=[IssuanceController],
    providers=[IssuanceService, JwtAuthGuard, RolesGuard],
    exports=[repository_token(TokenizationProposal), repository_token(TokenSeries)],
)
class IssuanceModule:
    pass
