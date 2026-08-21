from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class CreateAmlAlertDto(BaseModel):
    transaction_ref: str = Field(min_length=1)
    investor_id: int
    alert_type: str
    risk_score: float = Field(ge=0.0, le=100.0)
    rule_triggered: str | None = None


class AssignAlertDto(BaseModel):
    officer_id: int


class ResolveAlertDto(BaseModel):
    resolution_notes: str = Field(min_length=1, max_length=5000)
    status: str = Field(pattern="^(DISMISSED|ESCALATED)$")


class AmlAlertResponseDto(BaseModel):
    id: int
    transaction_ref: str
    investor_id: int
    alert_type: str
    risk_score: float
    status: str
    rule_triggered: str | None
    ml_model_version: str | None
    assigned_officer_id: int | None
    resolution_notes: str | None
    created_at: datetime
    resolved_at: datetime | None


class AmlAlertListDto(BaseModel):
    total: int
    items: list[AmlAlertResponseDto]


class GenerateReportDto(BaseModel):
    report_type: str = Field(pattern="^(QUARTERLY_IFSCA|ANNUAL_FINANCIALS)$")
    period_start: date
    period_end: date


class ComplianceReportResponseDto(BaseModel):
    id: int
    report_type: str
    period_start: date
    period_end: date
    generated_at: datetime
    generated_by_user_id: int
    aum_total_usd: float
    investor_count: int
    active_issuances_count: int
    currency_breakdown: dict
    file_storage_key: str | None
    status: str


class ComplianceReportListDto(BaseModel):
    total: int
    items: list[ComplianceReportResponseDto]


class DeletionRequestDto(BaseModel):
    entity_type: str = Field(min_length=1, max_length=100)
    entity_id: int
    reason: str = Field(min_length=1, max_length=2000)
