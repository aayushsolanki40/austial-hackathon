"""``InvestorsModule`` -- Phase-1.5 stub. Registers ``InvestorProfile``'s
repository for injection (``KycVerifiedGuard`` in ``modules/auth`` is its
only consumer today). Phase 2 will grow this into the real investors domain
module (``InvestorProfile``/``WalletMapping`` services, controllers, review
endpoints) -- kept intentionally minimal here.
"""

from austial import Module
from austial.orm import OrmModule, repository_token

from src.modules.investors.entities.investor_profile import InvestorProfile


@Module(
    imports=[OrmModule.for_feature([InvestorProfile])],
    exports=[repository_token(InvestorProfile)],
)
class InvestorsModule:
    pass
