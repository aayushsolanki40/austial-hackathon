"""``KycController`` -- Phase 2. ``@UseGuards(JwtAuthGuard, RolesGuard)`` applied once at the
controller level (``JwtAuthGuard`` must run first -- see that guard's own docstring on ordering);
each handler then carries its own ``@Roles(...)`` since this controller serves two different
audiences (investors submitting their own KYC vs. compliance officers reviewing everyone's),
unlike ``AdminController``'s single blanket ``ADMIN`` role.
"""

from __future__ import annotations

from austial import Body, Controller, Get, Param, Post, Query, Req, UseGuards

from src.i18n.i18n import t
from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.kyc.kyc_dto import (
    AddKycDocumentDto,
    CreateKycSubmissionDto,
    DocumentUploadUrlRequestDto,
    DocumentUploadUrlResponseDto,
    KycDocumentResponseDto,
    KycSubmissionListDto,
    KycSubmissionResponseDto,
    RecordRiskDisclosureConsentDto,
    RejectKycSubmissionDto,
    RiskDisclosureConsentResponseDto,
)
from src.modules.kyc.kyc_service import KycService

_DEFAULT_PAGE_SIZE = 50


def _current_user_id(request: Req) -> int:
    return int(request.state.user["sub"])


def _client_ip(request: Req) -> str | None:
    # Mirrors `AuditInterceptor`'s identical extraction -- see that class's docstring.
    return request.client.host if request.client else None


@Controller(t("kyc.route_prefix"))
@UseGuards(JwtAuthGuard, RolesGuard)
class KycController:
    def __init__(self, kyc_service: KycService):
        self.kyc_service = kyc_service

    # -- investor-facing ------------------------------------------------------------------

    @Post("submissions")
    @Roles("INVESTOR")
    async def create_submission(self, request: Req, dto: CreateKycSubmissionDto = Body()) -> KycSubmissionResponseDto:
        return await self.kyc_service.create_submission(_current_user_id(request), dto)

    @Get("submissions")
    @Roles("INVESTOR")
    async def list_my_submissions(self, request: Req) -> list[KycSubmissionResponseDto]:
        return await self.kyc_service.list_my_submissions(_current_user_id(request))

    @Get("submissions/:id")
    @Roles("INVESTOR")
    async def get_my_submission(self, request: Req, id: int = Param("id")) -> KycSubmissionResponseDto:
        return await self.kyc_service.get_my_submission(_current_user_id(request), id)

    @Post("submissions/:id/documents/upload-url")
    @Roles("INVESTOR")
    async def get_document_upload_url(
        self, request: Req, id: int = Param("id"), dto: DocumentUploadUrlRequestDto = Body()
    ) -> DocumentUploadUrlResponseDto:
        return await self.kyc_service.get_document_upload_url(_current_user_id(request), id, dto)

    @Post("submissions/:id/documents")
    @Roles("INVESTOR")
    async def add_document(
        self, request: Req, id: int = Param("id"), dto: AddKycDocumentDto = Body()
    ) -> KycDocumentResponseDto:
        return await self.kyc_service.add_document(_current_user_id(request), id, dto)

    @Post("submissions/:id/consent")
    @Roles("INVESTOR")
    async def record_consent(
        self, request: Req, id: int = Param("id"), dto: RecordRiskDisclosureConsentDto = Body()
    ) -> RiskDisclosureConsentResponseDto:
        return await self.kyc_service.record_consent(_current_user_id(request), id, dto, _client_ip(request))

    @Post("submissions/:id/submit")
    @Roles("INVESTOR")
    async def submit(self, request: Req, id: int = Param("id")) -> KycSubmissionResponseDto:
        return await self.kyc_service.submit(_current_user_id(request), id)

    # -- compliance-officer-facing (review queue) ------------------------------------------

    @Get("review-queue")
    @Roles("COMPLIANCE_OFFICER")
    async def list_pending_review(
        self, skip: int = Query("skip", default=0), take: int = Query("take", default=_DEFAULT_PAGE_SIZE)
    ) -> KycSubmissionListDto:
        return await self.kyc_service.list_pending_review(skip=skip, take=take)

    @Post("submissions/:id/approve")
    @Roles("COMPLIANCE_OFFICER")
    async def approve(self, request: Req, id: int = Param("id")) -> KycSubmissionResponseDto:
        return await self.kyc_service.approve(_current_user_id(request), id)

    @Post("submissions/:id/reject")
    @Roles("COMPLIANCE_OFFICER")
    async def reject(
        self, request: Req, id: int = Param("id"), dto: RejectKycSubmissionDto = Body()
    ) -> KycSubmissionResponseDto:
        return await self.kyc_service.reject(_current_user_id(request), id, dto.reason)
