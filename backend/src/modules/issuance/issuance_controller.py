"""``IssuanceController`` -- Phase 4. ``@UseGuards(JwtAuthGuard, RolesGuard)`` applied once at
the controller level (mirrors ``KycController``); per-handler ``@Roles(...)`` since this
controller, like ``KycController``, serves two different audiences -- issuers driving their own
proposal through ``DRAFT``/disclosure-upload/submit, and compliance officers (plus admins, per the
build plan's "compliance-officer or admin action" wording for the IFSCA-filing/approval steps)
running the review pipeline through to ``LAUNCHED`` and operating the token-series circuit
breaker.
"""

from __future__ import annotations

from austial import Body, Controller, Get, Param, Post, Query, Req, UseGuards

from src.i18n.i18n import t
from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.issuance.issuance_dto import (
    AddDisclosureDto,
    CreateProposalDto,
    DisclosureDocumentResponseDto,
    DisclosureUploadUrlRequestDto,
    DisclosureUploadUrlResponseDto,
    FileIfscaDto,
    IfscaApproveDto,
    LaunchProposalDto,
    ProposalDetailResponseDto,
    ProposalListDto,
    RecordSmartContractDeploymentDto,
    RejectProposalDto,
    TokenSeriesResponseDto,
)
from src.modules.issuance.issuance_service import IssuanceService

_DEFAULT_PAGE_SIZE = 50

_REVIEW_ROLES = ("COMPLIANCE_OFFICER", "ADMIN")


def _current_user_id(request: Req) -> int:
    return int(request.state.user["sub"])


@Controller(t("issuance.route_prefix"))
@UseGuards(JwtAuthGuard, RolesGuard)
class IssuanceController:
    def __init__(self, issuance_service: IssuanceService):
        self.issuance_service = issuance_service

    # -- issuer-facing: proposal lifecycle -----------------------------------------------------

    @Post("proposals")
    @Roles("ISSUER")
    async def create_proposal(self, request: Req, dto: CreateProposalDto = Body()) -> ProposalDetailResponseDto:
        return await self.issuance_service.create_proposal(_current_user_id(request), dto)

    @Get("proposals/mine")
    @Roles("ISSUER")
    async def list_my_proposals(
        self, request: Req, skip: int = Query("skip", default=0), take: int = Query("take", default=_DEFAULT_PAGE_SIZE)
    ) -> ProposalListDto:
        return await self.issuance_service.list_my_proposals(_current_user_id(request), skip=skip, take=take)

    @Get("proposals/mine/:id")
    @Roles("ISSUER")
    async def get_my_proposal(self, request: Req, id: int = Param("id")) -> ProposalDetailResponseDto:
        return await self.issuance_service.get_my_proposal(_current_user_id(request), id)

    @Post("proposals/mine/:id/submit")
    @Roles("ISSUER")
    async def submit_for_review(self, request: Req, id: int = Param("id")) -> ProposalDetailResponseDto:
        return await self.issuance_service.submit_for_review(_current_user_id(request), id)

    @Post("proposals/mine/:id/disclosures/upload-url")
    @Roles("ISSUER")
    async def get_disclosure_upload_url(
        self, request: Req, id: int = Param("id"), dto: DisclosureUploadUrlRequestDto = Body()
    ) -> DisclosureUploadUrlResponseDto:
        return await self.issuance_service.get_disclosure_upload_url(_current_user_id(request), id, dto)

    @Post("proposals/mine/:id/disclosures")
    @Roles("ISSUER")
    async def add_disclosure(
        self, request: Req, id: int = Param("id"), dto: AddDisclosureDto = Body()
    ) -> DisclosureDocumentResponseDto:
        return await self.issuance_service.add_disclosure(_current_user_id(request), id, dto)

    # -- compliance-officer/admin-facing: pipeline + review ------------------------------------

    @Get("proposals")
    @Roles(*_REVIEW_ROLES)
    async def list_pipeline(
        self,
        status: str | None = Query("status", default=None),
        skip: int = Query("skip", default=0),
        take: int = Query("take", default=_DEFAULT_PAGE_SIZE),
    ) -> ProposalListDto:
        return await self.issuance_service.list_pipeline(status=status, skip=skip, take=take)

    @Get("proposals/:id")
    @Roles(*_REVIEW_ROLES)
    async def get_proposal(self, id: int = Param("id")) -> ProposalDetailResponseDto:
        return await self.issuance_service.get_proposal(id)

    @Post("proposals/:id/compliance-approve")
    @Roles(*_REVIEW_ROLES)
    async def compliance_approve(self, request: Req, id: int = Param("id")) -> ProposalDetailResponseDto:
        return await self.issuance_service.compliance_approve(_current_user_id(request), id)

    @Post("proposals/:id/reject")
    @Roles(*_REVIEW_ROLES)
    async def reject(
        self, request: Req, id: int = Param("id"), dto: RejectProposalDto = Body()
    ) -> ProposalDetailResponseDto:
        return await self.issuance_service.reject(_current_user_id(request), id, dto)

    @Post("proposals/:id/file-ifsca")
    @Roles(*_REVIEW_ROLES)
    async def file_with_ifsca(
        self, request: Req, id: int = Param("id"), dto: FileIfscaDto = Body()
    ) -> ProposalDetailResponseDto:
        return await self.issuance_service.file_with_ifsca(_current_user_id(request), id, dto)

    @Post("proposals/:id/ifsca-approve")
    @Roles(*_REVIEW_ROLES)
    async def ifsca_approve(
        self, request: Req, id: int = Param("id"), dto: IfscaApproveDto = Body()
    ) -> ProposalDetailResponseDto:
        return await self.issuance_service.ifsca_approve(_current_user_id(request), id, dto)

    @Post("proposals/:id/launch")
    @Roles(*_REVIEW_ROLES)
    async def launch(
        self, request: Req, id: int = Param("id"), dto: LaunchProposalDto = Body()
    ) -> TokenSeriesResponseDto:
        return await self.issuance_service.launch(_current_user_id(request), id, dto)

    # -- token series: circuit breaker + smart contract deployment ----------------------------

    @Get("token-series/:id")
    @Roles(*_REVIEW_ROLES)
    async def get_token_series(self, id: int = Param("id")) -> TokenSeriesResponseDto:
        return await self.issuance_service.get_token_series(id)

    @Post("token-series/:id/pause")
    @Roles(*_REVIEW_ROLES)
    async def pause_token_series(self, request: Req, id: int = Param("id")) -> TokenSeriesResponseDto:
        return await self.issuance_service.pause_token_series(_current_user_id(request), id)

    @Post("token-series/:id/resume")
    @Roles(*_REVIEW_ROLES)
    async def resume_token_series(self, request: Req, id: int = Param("id")) -> TokenSeriesResponseDto:
        return await self.issuance_service.resume_token_series(_current_user_id(request), id)

    @Post("token-series/:id/smart-contract-deployment")
    @Roles(*_REVIEW_ROLES)
    async def record_smart_contract_deployment(
        self, request: Req, id: int = Param("id"), dto: RecordSmartContractDeploymentDto = Body()
    ) -> TokenSeriesResponseDto:
        return await self.issuance_service.record_smart_contract_deployment(_current_user_id(request), id, dto)
