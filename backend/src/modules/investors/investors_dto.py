from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from src.i18n.i18n import t
from src.modules.investors.entities.investor_profile import INVESTOR_TYPES, RISK_PROFILES
from src.modules.investors.entities.wallet_mapping import WALLET_CHAINS


class CreateInvestorProfileDto(BaseModel):
    investor_type: str
    jurisdiction: str
    risk_profile: str

    @field_validator("investor_type")
    @classmethod
    def _investor_type_must_be_known(cls, value: str) -> str:
        if value not in INVESTOR_TYPES:
            raise ValueError(t("investors.error.invalid_investor_type"))
        return value

    @field_validator("risk_profile")
    @classmethod
    def _risk_profile_must_be_known(cls, value: str) -> str:
        if value not in RISK_PROFILES:
            raise ValueError(t("investors.error.invalid_risk_profile"))
        return value

    @field_validator("jurisdiction")
    @classmethod
    def _jurisdiction_is_iso_alpha2(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 2 or not normalized.isalpha():
            raise ValueError(t("investors.error.invalid_jurisdiction"))
        return normalized


class InvestorProfileResponseDto(BaseModel):
    id: int
    investor_type: str | None
    jurisdiction: str | None
    risk_profile: str | None
    kyc_status: str
    created_at: datetime
    updated_at: datetime


class CreateWalletMappingDto(BaseModel):
    chain: str
    address: str = Field(min_length=1, max_length=255)
    label: str | None = Field(default=None, max_length=255)

    @field_validator("chain")
    @classmethod
    def _chain_must_be_known(cls, value: str) -> str:
        if value not in WALLET_CHAINS:
            raise ValueError(t("investors.error.invalid_chain"))
        return value


class WalletMappingResponseDto(BaseModel):
    id: int
    chain: str
    address: str
    label: str | None
    status: str
    created_at: datetime
