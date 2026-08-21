"""``RolesGuard`` -- Phase 1.4.

Reads the roles stashed by ``@Roles(...)`` off the handler (falling back to
the controller class) via ``Reflector``, and checks them against
``request.state.user["role"]`` -- which only exists if ``JwtAuthGuard`` ran
first in the same route's guard chain. A route with no ``@Roles(...)``
metadata at all is allowed through unconditionally (mirrors Nest's own
``RolesGuard`` recipe: "no roles required" != "deny").
"""

from __future__ import annotations

from austial import CanActivate, ExecutionContext, ForbiddenException, Reflector

from src.i18n.i18n import t
from src.modules.auth.decorators.roles_decorator import ROLES_METADATA


class RolesGuard(CanActivate):
    def __init__(self, reflector: Reflector):
        self.reflector = reflector

    async def can_activate(self, context: ExecutionContext) -> bool:
        required_roles: list[str] = self.reflector.get_all_and_override(
            ROLES_METADATA, [context.get_handler(), context.get_class()]
        )
        if not required_roles:
            return True

        request = context.get_request()
        user = getattr(request.state, "user", None)
        if user is None:
            raise ForbiddenException(t("auth.error.not_authenticated"))

        if user.get("role") not in required_roles:
            raise ForbiddenException(t("auth.error.insufficient_role"))
        return True
