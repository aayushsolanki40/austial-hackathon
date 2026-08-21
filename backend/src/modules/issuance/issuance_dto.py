from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from src.i18n.i18n import t
from src.modules.issuance.entities.disclosure_document import DISCLOSURE_TYPES

# -- proposals ---------------------------------------------------------------------------------


class CreateProposalDto(BaseModel):
    asset_id: int
    total_units: float = Field(gt=0)
    unit_price_usd: float = Field(gt=0)
    min_subscription_units: float = Field(gt=0)
    subscription_start_at: datetime
    subscription_end_at: datetime

    @model_validator(mode="after")
    def _subscription_window_is_valid(self) -> CreateProposalDto:
        if self.subscription_end_at <= self.subscription_start_at:
            raise ValueError(t("issuance.error.subscription_window_invalid"))
        if self.min_subscription_units > self.total_units:
            raise ValueError(t("issuance.error.min_subscription_exceeds_total"))
        return self


class RejectProposalDto(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class FileIfscaDto(BaseModel):
    filing_reference: str = Field(min_length=1, max_length=255)


class IfscaApproveDto(BaseModel):
    approval_reference: str = Field(min_length=1, max_length=255)


class LaunchProposalDto(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    contract_address: str | None = Field(default=None, max_length=255)


class DisclosureUploadUrlRequestDto(BaseModel):
    disclosure_type: str
    content_type: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def _disclosure_type_must_be_known(self) -> DisclosureUploadUrlRequestDto:
        if self.disclosure_type not in DISCLOSURE_TYPES:
            raise ValueError(t("issuance.error.invalid_disclosure_type"))
        return self


class DisclosureUploadUrlResponseDto(BaseModel):
    upload_url: str
    object_key: str


class AddDisclosureDto(BaseModel):
    disclosure_type: str
    object_key: str = Field(min_length=1)

    @model_validator(mode="after")
    def _disclosure_type_must_be_known(self) -> AddDisclosureDto:
        if self.disclosure_type not in DISCLOSURE_TYPES:
            raise ValueError(t("issuance.error.invalid_disclosure_type"))
        return self


class DisclosureDocumentResponseDto(BaseModel):
    id: int
    disclosure_type: str
    object_key: str
    version: int
    is_current: bool
    created_at: datetime


class ProposalResponseDto(BaseModel):
    id: int
    asset_id: int
    issuer_id: int
    total_units: float
    unit_price_usd: float
    min_subscription_units: float
    subscription_start_at: datetime
    subscription_end_at: datetime
    status: str
    ifsca_filing_reference: str | None
    ifsca_approval_reference: str | None
    rejection_reason: str | None
    reviewed_by_user_id: int | None
    created_at: datetime
    updated_at: datetime


class ProposalDetailResponseDto(ProposalResponseDto):
    """``ProposalResponseDto`` plus the live disclosure-completeness checklist -- mirrors
    ``KycSubmissionResponseDto`` embedding its `documents`/`consent`. ``missing_disclosure_types``
    is exactly what ``IssuanceService.launch`` itself checks, exposed here so the frontend's
    "disclosure upload with live completeness checklist" (per the build plan's frontend note) has
    something to render without duplicating the gate's logic client-side."""

    disclosures: list[DisclosureDocumentResponseDto] = Field(default_factory=list)
    missing_disclosure_types: list[str] = Field(default_factory=list)
    disclosures_complete: bool = False


class ProposalListDto(BaseModel):
    total: int
    items: list[ProposalResponseDto]


# -- token series / smart contract deployment ---------------------------------------------------


class TokenSeriesResponseDto(BaseModel):
    id: int
    proposal_id: int
    symbol: str
    total_supply: float
    contract_address: str | None
    paused: bool
    smart_contract_deployment_id: int | None
    created_at: datetime
    updated_at: datetime


class RecordSmartContractDeploymentDto(BaseModel):
    bytecode_hash: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=64)
    audit_report_ref: str | None = Field(default=None, max_length=255)


class SmartContractDeploymentResponseDto(BaseModel):
    id: int
    bytecode_hash: str
    version: str
    audit_report_ref: str | None
    deployed_at: datetime | None
    created_at: datetime
