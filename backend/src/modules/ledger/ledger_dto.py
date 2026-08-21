from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from src.i18n.i18n import t
from src.modules.ledger.entities.ledger_account import FREELY_CONVERTIBLE_CURRENCIES

# -- shared currency validation -----------------------------------------------------------------


def _validate_currency(value: str) -> str:
    """Rejects INR (and anything else outside the freely-convertible set) at the DTO layer --
    see ``LedgerAccount``'s docstring for why. Shared by every DTO below that carries a
    transaction-level ``currency`` field, mirroring ``IssuanceService``'s
    ``_disclosure_type_must_be_known`` "closed-set validator" convention."""
    normalized = value.strip().upper()
    if normalized not in FREELY_CONVERTIBLE_CURRENCIES:
        raise ValueError(t("ledger.error.currency_not_freely_convertible"))
    return normalized


# -- ledger account / entries -------------------------------------------------------------------


class LedgerAccountResponseDto(BaseModel):
    id: int
    currency: str
    available_balance: float
    locked_balance: float
    created_at: datetime
    updated_at: datetime


class LedgerEntryResponseDto(BaseModel):
    id: int
    entry_type: str
    amount: float
    currency: str
    balance_after: float
    reference_type: str
    reference_id: int | None
    created_at: datetime


class LedgerEntryListDto(BaseModel):
    total: int
    items: list[LedgerEntryResponseDto]


# -- funding instructions -------------------------------------------------------------------------


class RequestFundingInstructionDto(BaseModel):
    amount: float = Field(gt=0)
    currency: str = Field(default="USD")

    @field_validator("currency")
    @classmethod
    def _currency_is_freely_convertible(cls, value: str) -> str:
        return _validate_currency(value)


class FundingInstructionResponseDto(BaseModel):
    id: int
    reference_code: str
    amount: float
    currency: str
    status: str
    expires_at: datetime | None
    confirmed_at: datetime | None
    created_at: datetime

    # Static beneficiary/wire details -- see `LedgerService.request_funding_instruction`'s
    # docstring for why these are config-driven display fields, not entity columns.
    beneficiary_name: str
    beneficiary_bank_name: str
    beneficiary_account_number: str
    beneficiary_swift_bic: str


class FundingInstructionListDto(BaseModel):
    total: int
    items: list[FundingInstructionResponseDto]


class ConfirmFundingInstructionDto(BaseModel):
    # Optional -- omit for a plain manual confirm (the service derives a deterministic key from
    # the instruction's own id, so a double-click reuses the same key); pass an externally-issued
    # id (e.g. a bank-statement reference or webhook event id) when confirmation is driven by an
    # upstream system, so *that* system's own retry id is what's deduplicated on. See
    # `LedgerService.confirm_funding_instruction`'s docstring.
    idempotency_key: str | None = Field(default=None, max_length=255)


# -- payout instructions ---------------------------------------------------------------------------


class RecordPayoutInstructionDto(BaseModel):
    investor_id: int
    amount: float = Field(gt=0)
    currency: str = Field(default="USD")
    memo: str | None = Field(default=None, max_length=2000)
    # Mandatory (unlike funding's optional key) -- a payout has no prior `PENDING` row to key a
    # default off of, so the caller must supply a stable id for retries to actually be
    # idempotent. See `LedgerService.record_payout_instruction`'s docstring.
    idempotency_key: str = Field(min_length=1, max_length=255)

    @field_validator("currency")
    @classmethod
    def _currency_is_freely_convertible(cls, value: str) -> str:
        return _validate_currency(value)


class PayoutInstructionResponseDto(BaseModel):
    id: int
    investor_id: int
    amount: float
    currency: str
    status: str
    memo: str | None
    recorded_by_user_id: int | None
    recorded_at: datetime | None
    created_at: datetime
