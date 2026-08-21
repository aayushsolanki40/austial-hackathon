from __future__ import annotations

from austial import Controller, Get, Param, Query, Req, UseGuards

from src.i18n.i18n import t
from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.holdings.holdings_dto import HoldingListDto, HoldingResponseDto
from src.modules.holdings.holdings_service import HoldingsService

_DEFAULT_PAGE_SIZE = 50


def _current_user_id(request: Req) -> int:
    return int(request.state.user["sub"])


@Controller(t("holdings.route_prefix"))
@UseGuards(JwtAuthGuard, RolesGuard)
@Roles("INVESTOR")
class HoldingsController:
    def __init__(self, holdings_service: HoldingsService):
        self.holdings_service = holdings_service

    @Get("mine")
    async def list_my_holdings(
        self, request: Req, skip: int = Query("skip", default=0), take: int = Query("take", default=_DEFAULT_PAGE_SIZE)
    ) -> HoldingListDto:
        return await self.holdings_service.list_my_holdings(_current_user_id(request), skip=skip, take=take)

    @Get("mine/:id")
    async def get_my_holding(self, request: Req, id: int = Param("id")) -> HoldingResponseDto:
        return await self.holdings_service.get_my_holding(_current_user_id(request), id)
