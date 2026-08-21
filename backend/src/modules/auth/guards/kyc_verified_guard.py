"""``KycVerifiedGuard`` -- Phase 1.5.

Blocks any subscription/holding/payout route unless the requesting user's
``InvestorProfile.kyc_status`` is ``VERIFIED``. Must run after
``JwtAuthGuard`` in a route's guard chain (relies on ``request.state.user``).

Note on the query below: ``Repository.find_one_by({...})`` criteria keys can
only match plain ``Column()`` attributes, not a ``ManyToOne`` relation's
generated FK column (``austial.orm``'s ``EntityManager`` only resolves
criteria against ``EntityMetadata.columns``, which relations aren't part of)
-- so looking a profile up by its owning user goes through
``Repository.create_query_builder()`` instead, which is exactly the
documented escape hatch for anything ``FindOptions``/simple criteria dicts
can't express (see ``austial-py-doc/content/techniques/database.mdx``'s
``QueryBuilder`` section). Not a framework bug, just outside simple-criteria
scope.
"""

from __future__ import annotations

from austial import CanActivate, ExecutionContext, ForbiddenException
from austial.orm import InjectRepository, Repository

from src.i18n.i18n import t
from src.modules.investors.entities.investor_profile import InvestorProfile


class KycVerifiedGuard(CanActivate):
    def __init__(self, investors: Repository[InvestorProfile] = InjectRepository(InvestorProfile)):
        self.investors = investors

    async def can_activate(self, context: ExecutionContext) -> bool:
        request = context.get_request()
        user = getattr(request.state, "user", None)
        if user is None:
            raise ForbiddenException(t("auth.error.not_authenticated"))

        profile = await (
            self.investors.create_query_builder("investor_profile")
            .where("investor_profile.user_id = :user_id", {"user_id": int(user["sub"])})
            .get_one()
        )
        if profile is None or profile.kyc_status != "VERIFIED":
            raise ForbiddenException(t("investors.error.kyc_verification_required"))
        return True
