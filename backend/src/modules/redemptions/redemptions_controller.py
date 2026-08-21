from __future__ import annotations
from austial import Body, Controller, Get, Param, Post, Query, Req, UseGuards
from src.i18n.i18n import t
from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.kyc_verified_guard import KycVerifiedGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.redemptions.redemptions_dto import (
    CreateDistributionDto,
    CreateRedemptionRequestDto,
    DistributionListDto,
    DistributionResponseDto,
    ProcessDistributionResultDto,
    RedemptionRequestListDto,
    RedemptionRequestResponseDto,
    RejectRedemptionRequestDto,
)
from src.modules.redemptions.redemptions_service import RedemptionsService

_DEFAULT_PAGE_SIZE = 50

_OPS_ROLES = ("COMPLIANCE_OFFICER", "ADMIN")


def _current_user_id(request: Req) -> int:
    return int(request.state.user["sub"])


@Controller(t("redemptions.route_prefix"))
@UseGuards(JwtAuthGuard, RolesGuard)
class RedemptionsController:
    def __init__(self, redemptions_service: RedemptionsService):
        self.redemptions_service = redemptions_service

    # -- investor-facing: request / view / cancel ------------------------------------------------

    @Post()
    @Roles("INVESTOR")
    @UseGuards(JwtAuthGuard, RolesGuard, KycVerifiedGuard)
    async def create_request(
        self, request: Req, dto: CreateRedemptionRequestDto = Body()
    ) -> RedemptionRequestResponseDto:
        return await self.redemptions_service.create_request(_current_user_id(request), dto)

    @Get("mine")
    @Roles("INVESTOR")
    async def list_my_requests(
        self, request: Req, skip: int = Query("skip", default=0), take: int = Query("take", default=_DEFAULT_PAGE_SIZE)
    ) -> RedemptionRequestListDto:
        return await self.redemptions_service.list_my_requests(_current_user_id(request), skip=skip, take=take)

    @Get("mine/:id")
    @Roles("INVESTOR")
    async def get_my_request(self, request: Req, id: int = Param("id")) -> RedemptionRequestResponseDto:
        return await self.redemptions_service.get_my_request(_current_user_id(request), id)

    @Post("mine/:id/cancel")
    @Roles("INVESTOR")
    async def cancel_my_request(self, request: Req, id: int = Param("id")) -> RedemptionRequestResponseDto:
        return await self.redemptions_service.cancel_my_request(_current_user_id(request), id)

    # -- compliance-officer/admin-facing: list -----------------------------------------------------

    @Get()
    @Roles(*_OPS_ROLES)
    async def list_requests(
        self,
        status: str | None = Query("status", default=None),
        skip: int = Query("skip", default=0),
        take: int = Query("take", default=_DEFAULT_PAGE_SIZE),
    ) -> RedemptionRequestListDto:
        return await self.redemptions_service.list_requests(status=status, skip=skip, take=take)

    # -- distributions -- registered before the generic `:id` routes below, see module docstring --

    @Post("distributions")
    @Roles(*_OPS_ROLES)
    async def create_distribution(
        self, request: Req, dto: CreateDistributionDto = Body()
    ) -> DistributionResponseDto:
        return await self.redemptions_service.create_distribution(_current_user_id(request), dto)

    @Get("distributions")
    async def list_distributions(
        self,
        status: str | None = Query("status", default=None),
        skip: int = Query("skip", default=0),
        take: int = Query("take", default=_DEFAULT_PAGE_SIZE),
    ) -> DistributionListDto:
        return await self.redemptions_service.list_distributions(status=status, skip=skip, take=take)

    @Get("distributions/token-series/:series_id")
    async def list_distributions_for_series(
        self,
        series_id: int = Param("series_id"),
        skip: int = Query("skip", default=0),
        take: int = Query("take", default=_DEFAULT_PAGE_SIZE),
    ) -> DistributionListDto:
        return await self.redemptions_service.list_distributions_for_series(series_id, skip=skip, take=take)

    @Get("distributions/:id")
    async def get_distribution(self, id: int = Param("id")) -> DistributionResponseDto:
        return await self.redemptions_service.get_distribution(id)

    @Post("distributions/:id/process")
    @Roles(*_OPS_ROLES)
    async def process_distribution(self, request: Req, id: int = Param("id")) -> ProcessDistributionResultDto:
        return await self.redemptions_service.process_distribution(_current_user_id(request), id)

    # -- compliance-officer/admin-facing: single-request review pipeline -------------------------

    @Get(":id")
    @Roles(*_OPS_ROLES)
    async def get_request(self, id: int = Param("id")) -> RedemptionRequestResponseDto:
        return await self.redemptions_service.get_request(id)

    @Post(":id/approve")
    @Roles(*_OPS_ROLES)
    async def approve(self, request: Req, id: int = Param("id")) -> RedemptionRequestResponseDto:
        return await self.redemptions_service.approve(_current_user_id(request), id)

    @Post(":id/reject")
    @Roles(*_OPS_ROLES)
    async def reject(
        self, request: Req, id: int = Param("id"), dto: RejectRedemptionRequestDto = Body()
    ) -> RedemptionRequestResponseDto:
        return await self.redemptions_service.reject(_current_user_id(request), id, dto)

    @Post(":id/release")
    @Roles(*_OPS_ROLES)
    async def release(self, request: Req, id: int = Param("id")) -> RedemptionRequestResponseDto:
        return await self.redemptions_service.release(_current_user_id(request), id)

    @Post(":id/complete")
    @Roles(*_OPS_ROLES)
    async def complete(self, request: Req, id: int = Param("id")) -> RedemptionRequestResponseDto:
        return await self.redemptions_service.complete(_current_user_id(request), id)
