from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SubmitValuationFeedDto(BaseModel):
    token_series_id: int
    nav_per_unit: float = Field(gt=0)
    source: str = Field(min_length=1, max_length=255)
    reported_at: datetime


class ValuationFeedResponseDto(BaseModel):
    id: int
    token_series_id: int
    nav_per_unit: float
    source: str
    anomaly_score: float | None
    status: str
    reported_at: datetime
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None
    created_at: datetime


class ValuationFeedListDto(BaseModel):
    total: int
    items: list[ValuationFeedResponseDto]


class CurrentNavResponseDto(BaseModel):
    token_series_id: int
    nav_per_unit: float
    source: str
    as_of: datetime | None
