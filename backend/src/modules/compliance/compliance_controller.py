"""``ComplianceController`` -- Phase 8. AML alert management and IFSCA compliance reporting.

All routes guarded ``@Roles("COMPLIANCE_OFFICER", "ADMIN")`` -- compliance operations require
explicit authorization beyond mere authentication.
"""

from __future__ import annotations

from austial import Body, Controller, Get, Param, Patch, Post, Query, Req, UseGuards

from src.i18n.i18n import t
from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.compliance.compliance_dto import (
    AmlAlertListDto,
    AmlAlertResponseDto,
    AssignAlertDto,
    ComplianceReportListDto,
    ComplianceReportResponseDto,
    DeletionRequestDto,
    GenerateReportDto,
    ResolveAlertDto,
)
from src.modules.compliance.compliance_service import ComplianceService
from src.storage.object_storage_service import ObjectStorageService

_DEFAULT_PAGE_SIZE = 50


def _current_user_id(request: Req) -> int:
    return int(request.state.user["sub"])


@Controller(t("compliance.route_prefix"))
@UseGuards(JwtAuthGuard, RolesGuard)
@Roles("COMPLIANCE_OFFICER", "ADMIN")
class ComplianceController:
    def __init__(self, compliance_service: ComplianceService, storage: ObjectStorageService):
        self.compliance_service = compliance_service
        self.storage = storage

    # -- AML alerts --------------------------------------------------------------------------

    @Get("aml-alerts")
    async def list_alerts(
        self,
        request: Req,
        skip: int = Query("skip", default=0),
        take: int = Query("take", default=_DEFAULT_PAGE_SIZE),
        status: str | None = Query("status", default=None),
        assigned_to_me: bool = Query("assigned_to_me", default=False),
    ) -> AmlAlertListDto:
        assigned_officer_id = _current_user_id(request) if assigned_to_me else None
        return await self.compliance_service.list_alerts(
            skip=skip, take=take, status=status, assigned_officer_id=assigned_officer_id
        )

    @Patch("aml-alerts/:id/assign")
    async def assign_alert(
        self, request: Req, id: int = Param("id"), dto: AssignAlertDto = Body()
    ) -> AmlAlertResponseDto:
        return await self.compliance_service.assign_alert(id, dto.officer_id, _current_user_id(request))

    @Patch("aml-alerts/:id/resolve")
    async def resolve_alert(
        self, request: Req, id: int = Param("id"), dto: ResolveAlertDto = Body()
    ) -> AmlAlertResponseDto:
        return await self.compliance_service.resolve_alert(
            id, _current_user_id(request), dto.resolution_notes, dto.status
        )

    # -- Compliance reports ------------------------------------------------------------------

    @Post("reports/generate")
    async def generate_report(self, request: Req, dto: GenerateReportDto = Body()) -> ComplianceReportResponseDto:
        return await self.compliance_service.generate_quarterly_report(
            dto.report_type, dto.period_start, dto.period_end, _current_user_id(request)
        )

    @Get("reports")
    async def list_reports(
        self, skip: int = Query("skip", default=0), take: int = Query("take", default=_DEFAULT_PAGE_SIZE)
    ) -> ComplianceReportListDto:
        return await self.compliance_service.list_reports(skip=skip, take=take)

    @Get("reports/:id")
    async def get_report(self, id: int = Param("id")) -> ComplianceReportResponseDto:
        return await self.compliance_service.get_report_by_id(id)

    @Get("reports/:id/download")
    async def download_report(self, id: int = Param("id")) -> dict:
        report = await self.compliance_service.get_report_by_id(id)
        if not report.file_storage_key:
            from austial import NotFoundException

            raise NotFoundException(t("compliance.error.report_pdf_not_ready"))

        presigned_url = self.storage.generate_download_url(report.file_storage_key)
        return {"download_url": presigned_url}

    # -- Deletion requests (7-year retention) ------------------------------------------------

    @Post("deletion-requests")
    async def queue_deletion(self, request: Req, dto: DeletionRequestDto = Body()) -> dict:
        await self.compliance_service.queue_deletion_request(
            dto.entity_type, dto.entity_id, _current_user_id(request), dto.reason
        )
        return {"message": t("compliance.success.deletion_queued")}
