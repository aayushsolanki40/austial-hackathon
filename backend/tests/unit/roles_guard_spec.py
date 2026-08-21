"""Unit tests for ``RolesGuard`` -- Phase 1.4."""

from __future__ import annotations

import pytest
from austial import ExecutionContext, ForbiddenException, Reflector

from src.modules.auth.decorators.roles_decorator import Roles
from src.modules.auth.guards.roles_guard import RolesGuard
from tests.unit._request_factory import make_request


class _DummyController:
    pass


@Roles("ADMIN", "COMPLIANCE_OFFICER")
def _admin_only_handler() -> None:
    pass


def _unrestricted_handler() -> None:
    pass


@pytest.mark.asyncio
async def test_allows_request_when_no_roles_metadata_present():
    guard = RolesGuard(Reflector())
    request = make_request()
    request.state.user = {"sub": "1", "role": "INVESTOR"}
    context = ExecutionContext(request, _DummyController, _unrestricted_handler)

    assert await guard.can_activate(context) is True


@pytest.mark.asyncio
async def test_allows_request_when_user_has_required_role():
    guard = RolesGuard(Reflector())
    request = make_request()
    request.state.user = {"sub": "1", "role": "ADMIN"}
    context = ExecutionContext(request, _DummyController, _admin_only_handler)

    assert await guard.can_activate(context) is True


@pytest.mark.asyncio
async def test_denies_request_when_user_lacks_required_role():
    guard = RolesGuard(Reflector())
    request = make_request()
    request.state.user = {"sub": "1", "role": "INVESTOR"}
    context = ExecutionContext(request, _DummyController, _admin_only_handler)

    with pytest.raises(ForbiddenException):
        await guard.can_activate(context)


@pytest.mark.asyncio
async def test_denies_request_with_no_authenticated_user():
    guard = RolesGuard(Reflector())
    request = make_request()
    context = ExecutionContext(request, _DummyController, _admin_only_handler)

    with pytest.raises(ForbiddenException):
        await guard.can_activate(context)
