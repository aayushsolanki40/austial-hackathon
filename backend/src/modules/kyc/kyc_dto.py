from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.i18n.i18n import t
from src.modules.kyc.entities.kyc_document import KYC_DOCUMENT_TYPES


def _validate_iso_alpha2(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError(t("kyc.error.invalid_country_code"))
    return normalized


class CreateKycSubmissionDto(BaseModel):
    """Starts a new ``DRAFT`` submission -- identity fields are declared upfront so sanctions
    screening (``KycService.submit()``) always has something to screen against."""

    legal_name: str = Field(min_length=1, max_length=255)
    date_of_birth: date
    nationality: str

    @field_validator("nationality")
    @classmethod
    def _nationality_is_iso_alpha2(cls, value: str) -> str:
        return _validate_iso_alpha2(value)


class DocumentUploadUrlRequestDto(BaseModel):
    document_type: str
    content_type: str = Field(min_length=1, max_length=255)

    @field_validator("document_type")
    @classmethod
    def _document_type_must_be_known(cls, value: str) -> str:
        if value not in KYC_DOCUMENT_TYPES:
            raise ValueError(t("kyc.error.invalid_document_type"))
        return value


class DocumentUploadUrlResponseDto(BaseModel):
    upload_url: str
    object_key: str


class AddKycDocumentDto(BaseModel):
    document_type: str
    object_key: str = Field(min_length=1)

    @field_validator("document_type")
    @classmethod
    def _document_type_must_be_known(cls, value: str) -> str:
        if value not in KYC_DOCUMENT_TYPES:
            raise ValueError(t("kyc.error.invalid_document_type"))
        return value


class KycDocumentResponseDto(BaseModel):
    id: int
    document_type: str
    object_key: str
    ocr_result: dict[str, Any] | None
    created_at: datetime


class RecordRiskDisclosureConsentDto(BaseModel):
    """Body for ``POST /kyc/submissions/:id/consent`` -- the disclosure copy shown to the
    investor is versioned independently of this codebase (a content/legal change, not a
    schema change), so the caller must say exactly which version it displayed."""

    disclosure_version: str = Field(min_length=1, max_length=64)


class RiskDisclosureConsentResponseDto(BaseModel):
    id: int
    submission_id: int
    disclosure_version: str
    acknowledged_at: datetime


class KycSubmissionResponseDto(BaseModel):
    id: int
    investor_id: int
    status: str
    legal_name: str
    date_of_birth: date
    nationality: str
    submitted_at: datetime | None
    screening_result: dict[str, Any] | None
    reviewed_by_user_id: int | None
    review_notes: str | None
    created_at: datetime
    updated_at: datetime
    documents: list[KycDocumentResponseDto] = Field(default_factory=list)
    # `None` until the investor has acknowledged the risk disclosure for this submission --
    # see `RiskDisclosureConsent`'s docstring. The frontend's onboarding wizard should treat a
    # `null` here as "acknowledgment still required" for this submission.
    consent: RiskDisclosureConsentResponseDto | None = None


class KycSubmissionListDto(BaseModel):
    total: int
    items: list[KycSubmissionResponseDto]


class RejectKycSubmissionDto(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
