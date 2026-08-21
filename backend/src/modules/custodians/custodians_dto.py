from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateCustodianDto(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    ifsca_registration_no: str = Field(min_length=1, max_length=255)


class CustodianResponseDto(BaseModel):
    id: int
    name: str
    ifsca_registration_no: str
    ifsca_verified: bool
    verified_by_user_id: int | None
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CustodianListDto(BaseModel):
    total: int
    items: list[CustodianResponseDto]
