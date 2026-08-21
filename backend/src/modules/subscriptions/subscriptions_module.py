"""``SubscriptionsModule`` -- Phase 6. Registers only ``Subscription`` (the entity this module
owns) and imports ``HoldingsModule`` for direct ``TokenHolding`` repository access (``
SubscriptionsService.allocate``/``_upsert_holding`` writes ``TokenHolding`` rows directly) rather
than re-registering ``TokenHolding`` via its own ``OrmModule.for_feature(...)`` -- mirrors
``IssuanceModule``/``InvestorsModule``'s "the owning module registers + exports, everyone else
imports that module" convention."""

from austial import Module
from austial.orm import OrmModule, repository_token

from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.kyc_verified_guard import KycVerifiedGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.holdings.holdings_module import HoldingsModule
from src.modules.investors.investors_module import InvestorsModule
from src.modules.issuance.issuance_module import IssuanceModule
from src.modules.ledger.ledger_module import LedgerModule
from src.modules.subscriptions.entities.subscription import Subscription
from src.modules.subscriptions.subscriptions_controller import SubscriptionsController
from src.modules.subscriptions.subscriptions_service import SubscriptionsService


@Module(
    imports=[
        OrmModule.for_feature([Subscription]),
        InvestorsModule,
        IssuanceModule,
        LedgerModule,
        HoldingsModule,
    ],
    controllers=[SubscriptionsController],
    providers=[SubscriptionsService, JwtAuthGuard, RolesGuard, KycVerifiedGuard],
    exports=[repository_token(Subscription)],
)
class SubscriptionsModule:
    pass
