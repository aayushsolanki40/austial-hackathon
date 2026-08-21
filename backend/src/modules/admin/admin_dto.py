from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from src.i18n.i18n import t
from src.modules.auth.entities.user import USER_ROLES


class AdminDashboardSummaryDto(BaseModel):
    """``GET /admin/dashboard/summary``'s response.

    Phase-1 honesty note: only ``investor_count``, ``pending_kyc_count``, and ``users_by_role``
    are real, computed-from-live-data figures today. AUM (``sum(TokenHolding.quantity *
    avg_cost_usd)``) and every other holdings/valuation-derived metric belong on this dashboard
    per ``AUSTIAL_BUILD_PLAN.md`` Section 1.5, but ``TokenHolding`` doesn't exist yet (Phase 6) --
    so those fields are simply **absent** here rather than silently reported as ``0``, which would
    look like real (zero) AUM instead of "not computable yet". Add them back once the ``holdings``
    module ships, using ``Repository.sum()`` (now available in ``austial.orm`` -- see the
    build plan's framework-gap #2), not manual Python summation.
    """

    investor_count: int
    pending_kyc_count: int
    users_by_role: dict[str, int]


class AdminUserDto(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime


class AdminUserListDto(BaseModel):
    total: int
    items: list[AdminUserDto]


class UpdateUserRoleDto(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def _role_must_be_known(cls, value: str) -> str:
        if value not in USER_ROLES:
            raise ValueError(t("admin.error.invalid_role"))
        return value
