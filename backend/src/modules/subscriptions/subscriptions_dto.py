from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# -- marketplace (investor-facing, read-only) ---------------------------------------------------


class MarketplaceTokenSeriesDto(BaseModel):
    """A ``TokenSeries`` whose proposal is ``LAUNCHED``, not paused, and currently inside its
    subscription window -- see ``SubscriptionsService.list_marketplace``'s docstring."""

    id: int
    symbol: str
    asset_id: int
    asset_name: str
    asset_class: str
    issuer_id: int
    total_supply: float
    unit_price_usd: float
    min_subscription_units: float
    subscription_start_at: datetime
    subscription_end_at: datetime


class MarketplaceListDto(BaseModel):
    total: int
    items: list[MarketplaceTokenSeriesDto]


# -- subscriptions -------------------------------------------------------------------------------


class CreateSubscriptionDto(BaseModel):
    token_series_id: int
    units: float = Field(gt=0)


class SubscriptionResponseDto(BaseModel):
    id: int
    investor_id: int
    token_series_id: int
    symbol: str
    units: float
    amount_usd: float
    allocated_units: float | None
    status: str
    processed_by_user_id: int | None
    created_at: datetime
    updated_at: datetime


class SubscriptionListDto(BaseModel):
    total: int
    items: list[SubscriptionResponseDto]


class AllocationResultDto(BaseModel):
    """Return shape of the compliance-officer/admin-triggered allocation engine -- see
    ``SubscriptionsService.allocate``'s docstring for the pro-rata algorithm this summarizes."""

    token_series_id: int
    confirmed_subscription_count: int
    total_requested_units: float
    remaining_supply_before: float
    # `None` when there was nothing to allocate (`confirmed_subscription_count == 0`); `1.0` when
    # every `CONFIRMED` subscription was filled in full (no oversubscription); `< 1.0` under
    # pro-rata oversubscription.
    pro_rata_ratio: float | None
    allocated_subscription_count: int
