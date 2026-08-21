from __future__ import annotations

from austial import Body, Controller, Get, Param, Post, Query, Req, UseGuards

from src.i18n.i18n import t
from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.kyc_verified_guard import KycVerifiedGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.subscriptions.subscriptions_dto import (
    AllocationResultDto,
    CreateSubscriptionDto,
    MarketplaceListDto,
    SubscriptionListDto,
    SubscriptionResponseDto,
)
from src.modules.subscriptions.subscriptions_service import SubscriptionsService

_DEFAULT_PAGE_SIZE = 50

_OPS_ROLES = ("COMPLIANCE_OFFICER", "ADMIN")


def _current_user_id(request: Req) -> int:
    return int(request.state.user["sub"])


@Controller(t("subscriptions.route_prefix"))
@UseGuards(JwtAuthGuard, RolesGuard)
class SubscriptionsController:
    def __init__(self, subscriptions_service: SubscriptionsService):
        self.subscriptions_service = subscriptions_service

    # -- marketplace (investor-facing, read-only) ------------------------------------------------

    @Get("marketplace")
    @Roles("INVESTOR")
    async def list_marketplace(
        self, skip: int = Query("skip", default=0), take: int = Query("take", default=_DEFAULT_PAGE_SIZE)
    ) -> MarketplaceListDto:
        return await self.subscriptions_service.list_marketplace(skip=skip, take=take)

    # -- investor-facing: subscribe / view / cancel ----------------------------------------------

    @Post()
    @Roles("INVESTOR")
    @UseGuards(JwtAuthGuard, RolesGuard, KycVerifiedGuard)
    async def subscribe(self, request: Req, dto: CreateSubscriptionDto = Body()) -> SubscriptionResponseDto:
        return await self.subscriptions_service.subscribe(_current_user_id(request), dto)

    @Get("mine")
    @Roles("INVESTOR")
    async def list_my_subscriptions(
        self, request: Req, skip: int = Query("skip", default=0), take: int = Query("take", default=_DEFAULT_PAGE_SIZE)
    ) -> SubscriptionListDto:
        return await self.subscriptions_service.list_my_subscriptions(_current_user_id(request), skip=skip, take=take)

    @Get("mine/:id")
    @Roles("INVESTOR")
    async def get_my_subscription(self, request: Req, id: int = Param("id")) -> SubscriptionResponseDto:
        return await self.subscriptions_service.get_my_subscription(_current_user_id(request), id)

    @Post("mine/:id/cancel")
    @Roles("INVESTOR")
    async def cancel_my_subscription(self, request: Req, id: int = Param("id")) -> SubscriptionResponseDto:
        return await self.subscriptions_service.cancel_my_subscription(_current_user_id(request), id)

    # -- compliance-officer/admin-facing: ops actions + allocation -------------------------------

    @Get("token-series/:series_id")
    @Roles(*_OPS_ROLES)
    async def list_subscriptions_for_series(
        self,
        series_id: int = Param("series_id"),
        status: str | None = Query("status", default=None),
        skip: int = Query("skip", default=0),
        take: int = Query("take", default=_DEFAULT_PAGE_SIZE),
    ) -> SubscriptionListDto:
        return await self.subscriptions_service.list_subscriptions_for_series(
            series_id, status=status, skip=skip, take=take
        )

    @Post(":id/fund")
    @Roles(*_OPS_ROLES)
    async def mark_funded(self, request: Req, id: int = Param("id")) -> SubscriptionResponseDto:
        return await self.subscriptions_service.mark_funded(_current_user_id(request), id)

    @Post(":id/confirm")
    @Roles(*_OPS_ROLES)
    async def mark_confirmed(self, request: Req, id: int = Param("id")) -> SubscriptionResponseDto:
        return await self.subscriptions_service.mark_confirmed(_current_user_id(request), id)

    @Post(":id/refund")
    @Roles(*_OPS_ROLES)
    async def refund(self, request: Req, id: int = Param("id")) -> SubscriptionResponseDto:
        return await self.subscriptions_service.refund(_current_user_id(request), id)

    @Post("token-series/:series_id/allocate")
    @Roles(*_OPS_ROLES)
    async def allocate(self, request: Req, series_id: int = Param("series_id")) -> AllocationResultDto:
        return await self.subscriptions_service.allocate(_current_user_id(request), series_id)
