from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from src.i18n.i18n import t


def _validate_iso_alpha2(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError(t("issuers.error.invalid_jurisdiction"))
    return normalized


class CreateIssuerDto(BaseModel):
    legal_name: str = Field(min_length=1, max_length=255)
    registration_number: str = Field(min_length=1, max_length=255)
    registration_jurisdiction: str

    @field_validator("registration_jurisdiction")
    @classmethod
    def _jurisdiction_is_iso_alpha2(cls, value: str) -> str:
        return _validate_iso_alpha2(value)


class IssuerResponseDto(BaseModel):
    id: int
    legal_name: str
    registration_number: str
    registration_jurisdiction: str
    verification_status: str
    verified_by_user_id: int | None
    verified_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class IssuerListDto(BaseModel):
    total: int
    items: list[IssuerResponseDto]


class RejectIssuerDto(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
