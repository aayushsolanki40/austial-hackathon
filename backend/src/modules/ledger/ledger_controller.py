"""``LedgerController`` -- Phase 5. ``@UseGuards(JwtAuthGuard, RolesGuard)`` applied once at the
controller level (mirrors ``IssuanceController``/``KycController``); per-handler ``@Roles(...)``
since this controller, like those two, serves two different audiences -- investors managing their
own ``LedgerAccount``/requesting a ``FundingInstruction`` for themselves, and compliance
officers/admins confirming funding and recording payouts on any investor's account. See
``LedgerService``'s module docstring for the reasoning behind modelling funding confirmation as a
manual compliance-officer action rather than a public bank webhook.
"""

from __future__ import annotations

from austial import Body, Controller, Get, Param, Post, Query, Req, UseGuards

from src.i18n.i18n import t
from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.ledger.ledger_dto import (
    ConfirmFundingInstructionDto,
    FundingInstructionListDto,
    FundingInstructionResponseDto,
    LedgerAccountResponseDto,
    LedgerEntryListDto,
    PayoutInstructionResponseDto,
    RecordPayoutInstructionDto,
    RequestFundingInstructionDto,
)
from src.modules.ledger.ledger_service import LedgerService

_DEFAULT_PAGE_SIZE = 50

_OPS_ROLES = ("COMPLIANCE_OFFICER", "ADMIN")


def _current_user_id(request: Req) -> int:
    return int(request.state.user["sub"])


@Controller(t("ledger.route_prefix"))
@UseGuards(JwtAuthGuard, RolesGuard)
class LedgerController:
    def __init__(self, ledger_service: LedgerService):
        self.ledger_service = ledger_service

    # -- investor-facing: own account / funding -------------------------------------------------

    @Get("account")
    @Roles("INVESTOR")
    async def get_my_account(self, request: Req) -> LedgerAccountResponseDto:
        return await self.ledger_service.get_my_account(_current_user_id(request))

    @Get("entries")
    @Roles("INVESTOR")
    async def list_my_entries(
        self, request: Req, skip: int = Query("skip", default=0), take: int = Query("take", default=_DEFAULT_PAGE_SIZE)
    ) -> LedgerEntryListDto:
        return await self.ledger_service.list_my_entries(_current_user_id(request), skip=skip, take=take)

    @Post("funding-instructions")
    @Roles("INVESTOR")
    async def request_funding_instruction(
        self, request: Req, dto: RequestFundingInstructionDto = Body()
    ) -> FundingInstructionResponseDto:
        return await self.ledger_service.request_funding_instruction(_current_user_id(request), dto)

    @Get("funding-instructions/mine/:id")
    @Roles("INVESTOR")
    async def get_my_funding_instruction(self, request: Req, id: int = Param("id")) -> FundingInstructionResponseDto:
        return await self.ledger_service.get_my_funding_instruction(_current_user_id(request), id)

    # -- compliance-officer/admin-facing: confirmation + payouts --------------------------------

    @Get("funding-instructions")
    @Roles(*_OPS_ROLES)
    async def list_funding_instructions(
        self,
        status: str | None = Query("status", default=None),
        skip: int = Query("skip", default=0),
        take: int = Query("take", default=_DEFAULT_PAGE_SIZE),
    ) -> FundingInstructionListDto:
        return await self.ledger_service.list_funding_instructions(status=status, skip=skip, take=take)

    @Post("funding-instructions/:id/confirm")
    @Roles(*_OPS_ROLES)
    async def confirm_funding_instruction(
        self, request: Req, id: int = Param("id"), dto: ConfirmFundingInstructionDto = Body()
    ) -> FundingInstructionResponseDto:
        return await self.ledger_service.confirm_funding_instruction(_current_user_id(request), id, dto)

    @Post("payout-instructions")
    @Roles(*_OPS_ROLES)
    async def record_payout_instruction(
        self, request: Req, dto: RecordPayoutInstructionDto = Body()
    ) -> PayoutInstructionResponseDto:
        return await self.ledger_service.record_payout_instruction(_current_user_id(request), dto)
