"""``AdminController`` -- Phase 1.10. Every route here is ``ADMIN``-only:
``@Roles("ADMIN")`` + ``@UseGuards(JwtAuthGuard, RolesGuard)`` applied once at the controller
level (``JwtAuthGuard`` must run first -- see that guard's own docstring on ordering).
"""

from __future__ import annotations

from austial import Body, Controller, Get, Param, Patch, Query, Req, UseGuards

from src.i18n.i18n import t
from src.modules.admin.admin_dto import AdminDashboardSummaryDto, AdminUserDto, AdminUserListDto, UpdateUserRoleDto
from src.modules.admin.admin_service import AdminService
from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard

_DEFAULT_PAGE_SIZE = 50


def _actor_user_id(request: Req) -> int | None:
    user = getattr(request.state, "user", None)
    if not user or "sub" not in user:
        return None
    try:
        return int(user["sub"])
    except (TypeError, ValueError):
        return None


@Controller(t("admin.route_prefix"))
@Roles("ADMIN")
@UseGuards(JwtAuthGuard, RolesGuard)
class AdminController:
    def __init__(self, admin_service: AdminService):
        self.admin_service = admin_service

    @Get("dashboard/summary")
    # Handler-level `@Roles(...)` overrides the controller-level `@Roles("ADMIN")` above (see
    # `RolesGuard`'s `Reflector.get_all_and_override` -- handler metadata wins over class
    # metadata) -- this is the one route in this module `AUSTIAL_BUILD_PLAN.md` Section 1.5 opens
    # up to `COMPLIANCE_OFFICER` too, not just `ADMIN`.
    @Roles("ADMIN", "COMPLIANCE_OFFICER")
    async def dashboard_summary(self) -> AdminDashboardSummaryDto:
        return await self.admin_service.dashboard_summary()

    @Get("users")
    async def list_users(
        self,
        search: str | None = Query("search", default=None),
        skip: int = Query("skip", default=0),
        take: int = Query("take", default=_DEFAULT_PAGE_SIZE),
    ) -> AdminUserListDto:
        return await self.admin_service.list_users(search=search, skip=skip, take=take)

    @Patch("users/:id/role")
    async def update_user_role(
        self, request: Req, id: int = Param("id"), dto: UpdateUserRoleDto = Body()
    ) -> AdminUserDto:
        return await self.admin_service.update_user_role(id, dto.role, actor_user_id=_actor_user_id(request))

    @Patch("users/:id/suspend")
    async def suspend_user(self, request: Req, id: int = Param("id")) -> AdminUserDto:
        return await self.admin_service.suspend_user(id, actor_user_id=_actor_user_id(request))
