from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from src.i18n.i18n import t
from src.modules.ledger.entities.ledger_account import FREELY_CONVERTIBLE_CURRENCIES

# -- redemption requests --------------------------------------------------------------------------


class CreateRedemptionRequestDto(BaseModel):
    holding_id: int
    units_requested: float = Field(gt=0)


class RejectRedemptionRequestDto(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class RedemptionRequestResponseDto(BaseModel):
    id: int
    investor_id: int
    holding_id: int
    token_series_id: int
    symbol: str
    units_requested: float
    nav_per_unit_snapshot: float | None
    payout_amount: float | None
    status: str
    rejection_reason: str | None
    payout_instruction_id: int | None
    processed_by_user_id: int | None
    created_at: datetime
    updated_at: datetime


class RedemptionRequestListDto(BaseModel):
    total: int
    items: list[RedemptionRequestResponseDto]


# -- distributions ----------------------------------------------------------------------------


class CreateDistributionDto(BaseModel):
    token_series_id: int
    total_amount: float = Field(gt=0)
    currency: str = Field(default="USD")
    record_date: datetime

    @field_validator("currency")
    @classmethod
    def _currency_is_freely_convertible(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in FREELY_CONVERTIBLE_CURRENCIES:
            raise ValueError(t("ledger.error.currency_not_freely_convertible"))
        return normalized


class DistributionResponseDto(BaseModel):
    id: int
    token_series_id: int
    total_amount: float
    currency: str
    record_date: datetime
    status: str
    triggered_by_user_id: int | None
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DistributionListDto(BaseModel):
    total: int
    items: list[DistributionResponseDto]


class ProcessDistributionResultDto(BaseModel):
    """Return shape of the ops-triggered pro-rata payout run -- see
    ``RedemptionsService.process_distribution``'s docstring for the remainder-handling rule this
    summarizes."""

    distribution_id: int
    token_series_id: int
    total_amount: float
    holder_count: int
    total_credited: float
