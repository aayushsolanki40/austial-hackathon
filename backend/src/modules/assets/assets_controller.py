"""``AssetsController`` -- Phase 3. Issuer self-service only (asset submission and custodian
attachment are actions an issuer takes on their own assets) -- unlike ``CustodiansController``,
there is no compliance-officer-facing surface here yet since custodian *verification* already
lives on ``CustodiansController`` and asset-level compliance review is out of Phase 3's scope
per ``AUSTIAL_BUILD_PLAN.md``.
"""

from __future__ import annotations

from austial import Body, Controller, Get, Param, Post, Query, Req, UseGuards

from src.i18n.i18n import t
from src.modules.assets.assets_dto import AssetListDto, AssetResponseDto, AttachCustodianDto, CreateAssetDto
from src.modules.assets.assets_service import AssetsService
from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard

_DEFAULT_PAGE_SIZE = 50


def _current_user_id(request: Req) -> int:
    return int(request.state.user["sub"])


@Controller(t("assets.route_prefix"))
@Roles("ISSUER")
@UseGuards(JwtAuthGuard, RolesGuard)
class AssetsController:
    def __init__(self, assets_service: AssetsService):
        self.assets_service = assets_service

    @Post()
    async def create(self, request: Req, dto: CreateAssetDto = Body()) -> AssetResponseDto:
        return await self.assets_service.create_asset(_current_user_id(request), dto)

    @Get()
    async def list_mine(
        self, request: Req, skip: int = Query("skip", default=0), take: int = Query("take", default=_DEFAULT_PAGE_SIZE)
    ) -> AssetListDto:
        return await self.assets_service.list_my_assets(_current_user_id(request), skip=skip, take=take)

    @Get(":id")
    async def get_one(self, request: Req, id: int = Param("id")) -> AssetResponseDto:
        return await self.assets_service.get_my_asset(_current_user_id(request), id)

    @Post(":id/custodian")
    async def attach_custodian(
        self, request: Req, id: int = Param("id"), dto: AttachCustodianDto = Body()
    ) -> AssetResponseDto:
        return await self.assets_service.attach_custodian(_current_user_id(request), id, dto.custodian_id)
