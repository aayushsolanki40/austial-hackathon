"""``InvestorsModule`` -- Phase 2. Registers ``InvestorProfile`` and ``WalletMapping``
repositories, and the self-service ``InvestorsController``/``InvestorsService`` pair.

``exports=[repository_token(InvestorProfile)]`` is kept for ``AuthModule``, whose
``KycVerifiedGuard`` needs direct repository access to ``InvestorProfile`` (see that
guard's docstring) -- unrelated to this module's own controller/service, which is why
the export list isn't simply removed now that this module does more than Phase 1.5's
stub.
"""

from austial import Module
from austial.orm import OrmModule, repository_token

from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.investors.entities.wallet_mapping import WalletMapping
from src.modules.investors.investors_controller import InvestorsController
from src.modules.investors.investors_service import InvestorsService


@Module(
    imports=[OrmModule.for_feature([InvestorProfile, WalletMapping])],
    controllers=[InvestorsController],
    providers=[InvestorsService, JwtAuthGuard, RolesGuard],
    exports=[repository_token(InvestorProfile)],
)
class InvestorsModule:
    pass
