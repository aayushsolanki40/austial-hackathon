"""``InvestorsController`` -- Phase 2. All routes are ``INVESTOR``-only self-service:
create/read your own ``InvestorProfile``, add/list your own ``WalletMapping``s.
``@UseGuards(JwtAuthGuard, RolesGuard)`` + ``@Roles("INVESTOR")`` applied once at the
controller level, mirroring ``AdminController``'s single-audience pattern (unlike
``KycController``, which serves two different audiences and needs per-handler
``@Roles(...)``).
"""

from __future__ import annotations

from austial import Body, Controller, Get, Post, Req, UseGuards

from src.i18n.i18n import t
from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.investors.investors_dto import (
    CreateInvestorProfileDto,
    CreateWalletMappingDto,
    InvestorProfileResponseDto,
    WalletMappingResponseDto,
)
from src.modules.investors.investors_service import InvestorsService


def _current_user_id(request: Req) -> int:
    return int(request.state.user["sub"])


@Controller(t("investors.route_prefix"))
@Roles("INVESTOR")
@UseGuards(JwtAuthGuard, RolesGuard)
class InvestorsController:
    def __init__(self, investors_service: InvestorsService):
        self.investors_service = investors_service

    @Post("profile")
    async def create_profile(self, request: Req, dto: CreateInvestorProfileDto = Body()) -> InvestorProfileResponseDto:
        return await self.investors_service.create_profile(_current_user_id(request), dto)

    @Get("profile")
    async def get_my_profile(self, request: Req) -> InvestorProfileResponseDto:
        return await self.investors_service.get_my_profile(_current_user_id(request))

    @Post("wallets")
    async def add_wallet_mapping(self, request: Req, dto: CreateWalletMappingDto = Body()) -> WalletMappingResponseDto:
        return await self.investors_service.add_wallet_mapping(_current_user_id(request), dto)

    @Get("wallets")
    async def list_wallet_mappings(self, request: Req) -> list[WalletMappingResponseDto]:
        return await self.investors_service.list_wallet_mappings(_current_user_id(request))
