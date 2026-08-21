from __future__ import annotations

from austial import Body, Controller, Get, Param, Post, Query, Req, UseGuards

from src.i18n.i18n import t
from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.valuation.valuation_dto import (
    CurrentNavResponseDto,
    SubmitValuationFeedDto,
    ValuationFeedListDto,
    ValuationFeedResponseDto,
)
from src.modules.valuation.valuation_service import ValuationService

_DEFAULT_PAGE_SIZE = 50

_OPS_ROLES = ("COMPLIANCE_OFFICER", "ADMIN")


def _current_user_id(request: Req) -> int:
    return int(request.state.user["sub"])


@Controller(t("valuation.route_prefix"))
@UseGuards(JwtAuthGuard, RolesGuard)
class ValuationController:
    def __init__(self, valuation_service: ValuationService):
        self.valuation_service = valuation_service

    @Post("feeds")
    @Roles(*_OPS_ROLES)
    async def submit_feed(self, request: Req, dto: SubmitValuationFeedDto = Body()) -> ValuationFeedResponseDto:
        return await self.valuation_service.submit_feed(_current_user_id(request), dto)

    @Post("feeds/:id/approve")
    @Roles(*_OPS_ROLES)
    async def approve_quarantined_feed(self, request: Req, id: int = Param("id")) -> ValuationFeedResponseDto:
        return await self.valuation_service.approve_quarantined_feed(_current_user_id(request), id)

    @Get("feeds/token-series/:series_id")
    async def list_feeds_for_series(
        self,
        series_id: int = Param("series_id"),
        status: str | None = Query("status", default=None),
        skip: int = Query("skip", default=0),
        take: int = Query("take", default=_DEFAULT_PAGE_SIZE),
    ) -> ValuationFeedListDto:
        return await self.valuation_service.list_feeds_for_series(series_id, status=status, skip=skip, take=take)

    @Get("feeds/:id")
    async def get_feed(self, id: int = Param("id")) -> ValuationFeedResponseDto:
        return await self.valuation_service.get_feed(id)

    @Get("token-series/:series_id/current-nav")
    async def get_current_nav(self, series_id: int = Param("series_id")) -> CurrentNavResponseDto:
        return await self.valuation_service.get_current_nav(series_id)
