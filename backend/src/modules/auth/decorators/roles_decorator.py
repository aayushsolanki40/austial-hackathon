"""``@Roles(...)`` -- Phase 1.4. Stashes the required roles as route/controller
metadata, mirroring Nest's ``@SetMetadata('roles', roles)`` convenience
wrapper. Read back by ``RolesGuard`` via ``Reflector.get_all_and_override``.
"""

from __future__ import annotations

from collections.abc import Callable

from austial.core.metadata import set_metadata

ROLES_METADATA = "app:roles"


def Roles(*roles: str) -> Callable:
    """Usable on a controller (applies to every route) or a single handler,
    exactly like ``@UseGuards``/``@UseInterceptors``::

        @Roles("ADMIN", "COMPLIANCE_OFFICER")
        @UseGuards(JwtAuthGuard, RolesGuard)
        @Get("admin/dashboard")
        async def dashboard(self): ...
    """

    def decorator(target):
        set_metadata(ROLES_METADATA, list(roles))(target)
        return target

    return decorator
