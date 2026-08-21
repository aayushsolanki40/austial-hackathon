"""``CustodiansController`` -- Phase 3. Custodian *registry management* (create + IFSCA
verification) is ``COMPLIANCE_OFFICER``-only -- compliance officers are the ones who actually
check an IFSCA registration number against the regulator's registry, mirroring
``KycController``'s review-queue role split (not ``ADMIN``, which owns access-control actions
like role assignment, per ``AdminController``'s docstring). Read-only listing/lookup is opened up
to ``ISSUER`` too (handler-level ``@Roles(...)`` override, same pattern as
``AdminController.dashboard_summary``) so the issuer portal's asset-submission form can populate
a "select a verified custodian" control without needing its own registry endpoint.
"""

from __future__ import annotations

from austial import Body, Controller, Get, Param, Post, Query, Req, UseGuards

from src.i18n.i18n import t
from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.custodians.custodians_dto import CreateCustodianDto, CustodianListDto, CustodianResponseDto
from src.modules.custodians.custodians_service import CustodiansService

_DEFAULT_PAGE_SIZE = 50


def _current_user_id(request: Req) -> int:
    return int(request.state.user["sub"])


@Controller(t("custodians.route_prefix"))
@Roles("COMPLIANCE_OFFICER")
@UseGuards(JwtAuthGuard, RolesGuard)
class CustodiansController:
    def __init__(self, custodians_service: CustodiansService):
        self.custodians_service = custodians_service

    @Post()
    async def create(self, dto: CreateCustodianDto = Body()) -> CustodianResponseDto:
        return await self.custodians_service.create(dto)

    @Get()
    @Roles("COMPLIANCE_OFFICER", "ISSUER")
    async def list(
        self, skip: int = Query("skip", default=0), take: int = Query("take", default=_DEFAULT_PAGE_SIZE)
    ) -> CustodianListDto:
        return await self.custodians_service.list(skip=skip, take=take)

    @Get(":id")
    @Roles("COMPLIANCE_OFFICER", "ISSUER")
    async def get_one(self, id: int = Param("id")) -> CustodianResponseDto:
        return await self.custodians_service.get_by_id(id)

    @Post(":id/verify")
    async def verify(self, request: Req, id: int = Param("id")) -> CustodianResponseDto:
        return await self.custodians_service.verify(_current_user_id(request), id)
