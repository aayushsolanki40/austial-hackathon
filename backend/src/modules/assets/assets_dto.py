from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.modules.assets.entities.asset import ASSET_CLASSES


class CreateAssetDto(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    asset_class: str = Field(pattern="^(" + "|".join(ASSET_CLASSES) + ")$")
    description: str | None = Field(default=None, max_length=4000)


class AttachCustodianDto(BaseModel):
    custodian_id: int


class AssetResponseDto(BaseModel):
    id: int
    issuer_id: int
    custodian_id: int | None
    name: str
    asset_class: str
    description: str | None
    custodian_verified: bool
    # Not a stored column -- see `Asset`'s docstring -- always `custodian is not None` (which,
    # given `attach_custodian`'s enforcement, also implies `custodian_verified is True`).
    tokenization_ready: bool
    created_at: datetime
    updated_at: datetime


class AssetListDto(BaseModel):
    total: int
    items: list[AssetResponseDto]
