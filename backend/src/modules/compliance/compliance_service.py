"""``ComplianceService`` -- Phase 8. AML alert management and IFSCA compliance reporting.

★ Pluggable ML seam: ``create_aml_alert`` accepts rule-based alerts today (Phase 8) but is
structured to accept ML-scored alerts (Phase 9) without refactoring -- the entity already has
both ``rule_triggered`` and ``ml_model_version`` columns, and the service just writes whichever
is provided.

★ 7-year retention: ``queue_deletion_request`` never deletes -- it only queues. Actual deletion
is not implemented (IFSCA mandates 7-year retention, so deletion is a compliance-officer manual
review workflow, not an automated API operation).

★ Aggregation queries: ``generate_quarterly_report`` uses ``Repository.sum()`` and
``Repository.count()`` from Phase 1.0(b) ORM extensions -- no raw SQL.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from austial import ConflictException, Injectable, NotFoundException
from austial.orm import FindOptions, InjectRepository, Repository

from src.i18n.i18n import t
from src.jobs.celery_app import CELERY_APP_TOKEN
from src.modules.auth.entities.user import User
from src.modules.compliance.compliance_dto import (
    AmlAlertListDto,
    AmlAlertResponseDto,
    ComplianceReportListDto,
    ComplianceReportResponseDto,
)
from src.modules.compliance.entities.aml_alert import AmlAlert
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.compliance.entities.compliance_report import ComplianceReport
from src.modules.holdings.entities.token_holding import TokenHolding
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.issuance.entities.token_series import TokenSeries
from src.modules.ledger.entities.ledger_entry import FREELY_CONVERTIBLE_CURRENCIES, LedgerEntry

_RESOLUTION_STATUSES = {"DISMISSED", "ESCALATED"}


def _aml_alert_to_dto(alert: AmlAlert) -> AmlAlertResponseDto:
    return AmlAlertResponseDto(
        id=alert.id,
        transaction_ref=alert.transaction_ref,
        investor_id=alert.investor.id,
        alert_type=alert.alert_type,
        risk_score=float(alert.risk_score),
        status=alert.status,
        rule_triggered=alert.rule_triggered,
        ml_model_version=alert.ml_model_version,
        assigned_officer_id=alert.assigned_officer.id if alert.assigned_officer else None,
        resolution_notes=alert.resolution_notes,
        created_at=alert.created_at,
        resolved_at=alert.resolved_at,
    )


def _compliance_report_to_dto(report: ComplianceReport) -> ComplianceReportResponseDto:
    return ComplianceReportResponseDto(
        id=report.id,
        report_type=report.report_type,
        period_start=report.period_start,
        period_end=report.period_end,
        generated_at=report.generated_at,
        generated_by_user_id=report.generated_by_user_id,
        aum_total_usd=float(report.aum_total_usd),
        investor_count=report.investor_count,
        active_issuances_count=report.active_issuances_count,
        currency_breakdown=report.currency_breakdown,
        file_storage_key=report.file_storage_key,
        status=report.status,
    )


@Injectable()
class ComplianceService:
    def __init__(
        self,
        users: Repository[User] = InjectRepository(User),
        investors: Repository[InvestorProfile] = InjectRepository(InvestorProfile),
        aml_alerts: Repository[AmlAlert] = InjectRepository(AmlAlert),
        compliance_reports: Repository[ComplianceReport] = InjectRepository(ComplianceReport),
        holdings: Repository[TokenHolding] = InjectRepository(TokenHolding),
        token_series: Repository[TokenSeries] = InjectRepository(TokenSeries),
        ledger_entries: Repository[LedgerEntry] = InjectRepository(LedgerEntry),
        audit_logs: Repository[AuditLog] = InjectRepository(AuditLog),
        celery_app=CELERY_APP_TOKEN,
    ):
        self.users = users
        self.investors = investors
        self.aml_alerts = aml_alerts
        self.compliance_reports = compliance_reports
        self.holdings = holdings
        self.token_series = token_series
        self.ledger_entries = ledger_entries
        self.audit_logs = audit_logs
        self.celery_app = celery_app

    # -- AML alert management -----------------------------------------------------------------

    async def create_aml_alert(
        self,
        transaction_ref: str,
        investor_id: int,
        alert_type: str,
        risk_score: float,
        rule_triggered: str | None = None,
        ml_model_version: str | None = None,
    ) -> AmlAlertResponseDto:
        investor = await self.investors.find_one(FindOptions(where={"id": investor_id}))
        if investor is None:
            raise NotFoundException(t("compliance.error.investor_not_found"))

        alert = await self.aml_alerts.save(
            AmlAlert(  # type: ignore[call-arg]
                transaction_ref=transaction_ref,
                investor=investor,
                alert_type=alert_type,
                risk_score=risk_score,
                rule_triggered=rule_triggered,
                ml_model_version=ml_model_version,
                status="OPEN",
            )
        )
        return _aml_alert_to_dto(alert)

    async def list_alerts(
        self, *, skip: int, take: int, status: str | None = None, assigned_officer_id: int | None = None
    ) -> AmlAlertListDto:
        query = self.aml_alerts.create_query_builder("a")
        if status:
            query = query.where_eq("a.status", status, cast_text=True)
        if assigned_officer_id is not None:
            query = query.where("a.assigned_officer_id = :officer_id", {"officer_id": assigned_officer_id})

        alerts, total = await query.add_order_by("a.created_at", "DESC").skip(skip).take(take).get_many_and_count()
        return AmlAlertListDto(total=total, items=[_aml_alert_to_dto(alert) for alert in alerts])

    async def assign_alert(self, alert_id: int, officer_id: int, actor_user_id: int) -> AmlAlertResponseDto:
        alert = await self._get_alert_or_raise(alert_id)
        officer = await self._get_user_or_raise(officer_id)

        if officer.role not in ("COMPLIANCE_OFFICER", "ADMIN"):
            raise ConflictException(t("compliance.error.officer_role_required"))

        before_state = {"assigned_officer_id": alert.assigned_officer.id if alert.assigned_officer else None}
        await self.aml_alerts.update({"id": alert_id}, {"assigned_officer_id": officer_id})
        await self._write_audit_log(
            alert_id=alert_id,
            actor_user_id=actor_user_id,
            action="compliance.aml_alert.assigned",
            before_state=before_state,
            after_state={"assigned_officer_id": officer_id},
        )
        return await self.get_alert_by_id(alert_id)

    async def resolve_alert(
        self, alert_id: int, officer_id: int, resolution_notes: str, new_status: str
    ) -> AmlAlertResponseDto:
        if new_status not in _RESOLUTION_STATUSES:
            raise ConflictException(
                t("compliance.error.invalid_resolution_status").format(status=new_status, allowed=", ".join(_RESOLUTION_STATUSES))
            )

        alert = await self._get_alert_or_raise(alert_id)
        if alert.status not in ("OPEN", "UNDER_REVIEW"):
            raise ConflictException(t("compliance.error.alert_already_resolved"))

        before_state = {"status": alert.status}
        now = datetime.now(UTC).replace(tzinfo=None)
        await self.aml_alerts.update(
            {"id": alert_id}, {"status": new_status, "resolution_notes": resolution_notes, "resolved_at": now}
        )
        await self._write_audit_log(
            alert_id=alert_id,
            actor_user_id=officer_id,
            action="compliance.aml_alert.resolved",
            before_state=before_state,
            after_state={"status": new_status, "resolution_notes": resolution_notes},
        )
        return await self.get_alert_by_id(alert_id)

    async def get_alert_by_id(self, alert_id: int) -> AmlAlertResponseDto:
        alert = await self._get_alert_or_raise(alert_id)
        return _aml_alert_to_dto(alert)

    # -- Compliance reporting -----------------------------------------------------------------

    async def generate_quarterly_report(
        self, report_type: str, period_start: date, period_end: date, officer_id: int
    ) -> ComplianceReportResponseDto:
        # Aggregate AUM from TokenHolding (sum of quantity * avg_cost_usd for ACTIVE holdings).
        # Using Repository.sum() from Phase 1.0(b) ORM extensions.
        aum_total_usd = await self._compute_aum()

        # Investor count (distinct VERIFIED investors).
        investor_count = await self.investors.count(FindOptions(where={"kyc_status": "VERIFIED"}))

        # Active issuances count (TokenSeries with paused=False).
        active_issuances_count = await self.token_series.count(FindOptions(where={"paused": False}))

        # Currency breakdown from LedgerEntry (sum by currency).
        currency_breakdown = await self._compute_currency_breakdown()

        report = await self.compliance_reports.save(
            ComplianceReport(  # type: ignore[call-arg]
                report_type=report_type,
                period_start=period_start,
                period_end=period_end,
                generated_by_user_id=officer_id,
                aum_total_usd=aum_total_usd,
                investor_count=investor_count,
                active_issuances_count=active_issuances_count,
                currency_breakdown=currency_breakdown,
                status="DRAFT",
            )
        )

        # Queue Celery task to generate PDF asynchronously.
        self.celery_app.send_task("jobs.generate_report_pdf", args=[report.id])

        return _compliance_report_to_dto(report)

    async def list_reports(self, *, skip: int, take: int) -> ComplianceReportListDto:
        reports, total = await (
            self.compliance_reports.create_query_builder("r")
            .add_order_by("r.generated_at", "DESC")
            .skip(skip)
            .take(take)
            .get_many_and_count()
        )
        return ComplianceReportListDto(total=total, items=[_compliance_report_to_dto(report) for report in reports])

    async def get_report_by_id(self, report_id: int) -> ComplianceReportResponseDto:
        report = await self._get_report_or_raise(report_id)
        return _compliance_report_to_dto(report)

    # -- Deletion requests (7-year retention) -------------------------------------------------

    async def queue_deletion_request(self, entity_type: str, entity_id: int, requested_by: int, reason: str) -> None:
        """Queues a deletion request (7-year retention rule -- doesn't execute immediately).

        Real implementation would write to a ``DeletionRequest`` entity (not built yet) and trigger
        a compliance-officer review workflow. For now, just write an audit log entry to prove the
        request was made.
        """
        await self._write_audit_log(
            alert_id=None,
            actor_user_id=requested_by,
            action="compliance.deletion_request.queued",
            before_state={},
            after_state={"entity_type": entity_type, "entity_id": entity_id, "reason": reason},
        )

    # -- Internals ----------------------------------------------------------------------------

    async def _compute_aum(self) -> float:
        """Compute total AUM (sum of quantity * avg_cost_usd for ACTIVE holdings).

        Note: since Repository.sum() doesn't support computed expressions (quantity * avg_cost_usd),
        we fetch all ACTIVE holdings and compute in Python. This is acceptable for demo scale but
        would need raw SQL for production scale.
        """
        active_holdings = await self.holdings.find(FindOptions(where={"status": "ACTIVE"}))
        aum = sum(
            (Decimal(str(h.quantity)) * Decimal(str(h.avg_cost_usd)) for h in active_holdings), Decimal("0")
        )
        return float(aum)

    async def _compute_currency_breakdown(self) -> dict:
        """Compute currency breakdown (sum of amount by currency from LedgerEntry)."""
        # Repository.sum() with group_by returns list[dict[str, Any]] where each dict has the
        # group-by column(s) plus a "sum" key with the aggregated value.
        grouped = await self.ledger_entries.sum("amount", group_by=["currency"])
        return {row["currency"]: str(row["sum"]) for row in grouped}

    async def _get_alert_or_raise(self, alert_id: int) -> AmlAlert:
        alert = await self.aml_alerts.find_one(FindOptions(where={"id": alert_id}))
        if alert is None:
            raise NotFoundException(t("compliance.error.alert_not_found"))
        return alert

    async def _get_report_or_raise(self, report_id: int) -> ComplianceReport:
        report = await self.compliance_reports.find_one(FindOptions(where={"id": report_id}))
        if report is None:
            raise NotFoundException(t("compliance.error.report_not_found"))
        return report

    async def _get_user_or_raise(self, user_id: int) -> User:
        user = await self.users.find_one(FindOptions(where={"id": user_id}))
        if user is None:
            raise NotFoundException(t("compliance.error.user_not_found"))
        return user

    async def _write_audit_log(
        self, *, alert_id: int | None, actor_user_id: int | None, action: str, before_state: dict, after_state: dict
    ) -> None:
        await self.audit_logs.save(
            AuditLog(  # type: ignore[call-arg]
                actor_user_id=actor_user_id,
                action=action,
                entity_type="AmlAlert" if alert_id else "ComplianceReport",
                entity_id=str(alert_id) if alert_id else None,
                before_state=before_state,
                after_state=after_state,
                ip_address=None,
            )
        )
