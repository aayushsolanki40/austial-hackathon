






































from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HoldingResponseDto(BaseModel):
    id: int
    investor_id: int
    token_series_id: int
    symbol: str
    quantity: float
    avg_cost_usd: float
    status: str
    custodian_confirmation_ref: str | None
    created_at: datetime
    updated_at: datetime


class HoldingListDto(BaseModel):
    total: int
    items: list[HoldingResponseDto]
