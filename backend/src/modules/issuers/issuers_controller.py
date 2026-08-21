"""``IssuersController`` -- Phase 3. Serves two audiences under one route prefix, mirroring
``KycController``'s split: issuer self-service (``@Roles("ISSUER")``) and the compliance
fit-and-proper review queue (``@Roles("COMPLIANCE_OFFICER")``) -- ``@UseGuards(JwtAuthGuard,
RolesGuard)`` applied once at the controller level, per-handler ``@Roles(...)`` on each route.
"""

from __future__ import annotations

from austial import Body, Controller, Get, Param, Post, Query, Req, UseGuards

from src.i18n.i18n import t
from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.issuers.issuers_dto import CreateIssuerDto, IssuerListDto, IssuerResponseDto, RejectIssuerDto
from src.modules.issuers.issuers_service import IssuersService

_DEFAULT_PAGE_SIZE = 50


def _current_user_id(request: Req) -> int:
    return int(request.state.user["sub"])


@Controller(t("issuers.route_prefix"))
@UseGuards(JwtAuthGuard, RolesGuard)
class IssuersController:
    def __init__(self, issuers_service: IssuersService):
        self.issuers_service = issuers_service

    # -- issuer self-service ------------------------------------------------------------------

    @Post("profile")
    @Roles("ISSUER")
    async def create_profile(self, request: Req, dto: CreateIssuerDto = Body()) -> IssuerResponseDto:
        return await self.issuers_service.create_profile(_current_user_id(request), dto)

    @Get("profile")
    @Roles("ISSUER")
    async def get_my_profile(self, request: Req) -> IssuerResponseDto:
        return await self.issuers_service.get_my_profile(_current_user_id(request))

    # -- compliance-officer-facing (fit-and-proper review queue) ------------------------------

    @Get("review-queue")
    @Roles("COMPLIANCE_OFFICER")
    async def list_pending_review(
        self, skip: int = Query("skip", default=0), take: int = Query("take", default=_DEFAULT_PAGE_SIZE)
    ) -> IssuerListDto:
        return await self.issuers_service.list_pending_review(skip=skip, take=take)

    @Post(":id/approve")
    @Roles("COMPLIANCE_OFFICER")
    async def approve(self, request: Req, id: int = Param("id")) -> IssuerResponseDto:
        return await self.issuers_service.approve(_current_user_id(request), id)

    @Post(":id/reject")
    @Roles("COMPLIANCE_OFFICER")
    async def reject(self, request: Req, id: int = Param("id"), dto: RejectIssuerDto = Body()) -> IssuerResponseDto:
        return await self.issuers_service.reject(_current_user_id(request), id, dto.reason)
