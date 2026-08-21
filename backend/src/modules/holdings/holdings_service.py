"""``HoldingsService`` -- Phase 6. Read-only from this side; ``TokenHolding`` rows are only ever
written by ``SubscriptionsService.allocate``/``_upsert_holding`` (see that module's docstring)."""

from __future__ import annotations

from austial import Injectable, NotFoundException
from austial.orm import FindOptions, InjectRepository, Repository

from src.i18n.i18n import t
from src.modules.holdings.entities.token_holding import TokenHolding
from src.modules.holdings.holdings_dto import HoldingListDto, HoldingResponseDto
from src.modules.investors.entities.investor_profile import InvestorProfile


def _to_dto(holding: TokenHolding) -> HoldingResponseDto:
    return HoldingResponseDto(
        id=holding.id,
        investor_id=holding.investor.id,
        token_series_id=holding.token_series.id,
        symbol=holding.token_series.symbol,
        quantity=float(holding.quantity),
        avg_cost_usd=float(holding.avg_cost_usd),
        status=holding.status,
        custodian_confirmation_ref=holding.custodian_confirmation_ref,
        created_at=holding.created_at,
        updated_at=holding.updated_at,
    )


@Injectable()
class HoldingsService:
    def __init__(
        self,
        investor_profiles: Repository[InvestorProfile] = InjectRepository(InvestorProfile),
        holdings: Repository[TokenHolding] = InjectRepository(TokenHolding),
    ):
        self.investor_profiles = investor_profiles
        self.holdings = holdings

    async def list_my_holdings(self, user_id: int, *, skip: int, take: int) -> HoldingListDto:
        investor = await self._get_investor_by_user_or_raise(user_id)
        holdings, total = await (
            self.holdings.create_query_builder("h")
            .left_join_and_select("h.token_series", "series")
            .left_join_and_select("h.investor", "investor")
            .where("h.investor_id = :investor_id", {"investor_id": investor.id})
            .add_order_by("h.id", "DESC")
            .skip(skip)
            .take(take)
            .get_many_and_count()
        )
        return HoldingListDto(total=total, items=[_to_dto(h) for h in holdings])

    async def get_my_holding(self, user_id: int, holding_id: int) -> HoldingResponseDto:
        investor = await self._get_investor_by_user_or_raise(user_id)
        holding = await self.holdings.find_one(
            FindOptions(where={"id": holding_id}, relations=["investor", "token_series"])
        )
        if holding is None or holding.investor.id != investor.id:
            # `NotFoundException`, not `ForbiddenException` -- mirrors `SubscriptionsService.
            # _get_own_subscription_or_raise`: don't leak the existence of another investor's holding.
            raise NotFoundException(t("holdings.error.holding_not_found"))
        return _to_dto(holding)

    async def _get_investor_by_user_or_raise(self, user_id: int) -> InvestorProfile:
        investor = await (
            self.investor_profiles.create_query_builder("investor")
            .where("investor.user_id = :user_id", {"user_id": user_id})
            .get_one()
        )
        if investor is None:
            raise NotFoundException(t("holdings.error.investor_profile_required"))
        return investor
