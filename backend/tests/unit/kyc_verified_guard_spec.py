"""Unit tests for ``KycVerifiedGuard`` -- Phase 1.5."""

from __future__ import annotations

import pytest
from austial import ExecutionContext, ForbiddenException
from austial.orm import DataSource, OrmModule
from austial.testing import Test

from src.modules.auth.entities.user import User
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.investors.investors_module import InvestorsModule
from tests.unit._request_factory import make_request


async def _build_guard_and_repos():
    module = await Test.create_testing_module(
        imports=[
            OrmModule.for_root(
                type_="sqlite",
                url="sqlite+aiosqlite:///:memory:",
                entities=[User, InvestorProfile],
                synchronize=True,
            ),
            OrmModule.for_feature([User]),
            InvestorsModule,
        ]
    ).compile()
    await module.get(DataSource).initialize()
    from src.modules.auth.guards.kyc_verified_guard import KycVerifiedGuard

    guard = module.get(KycVerifiedGuard)
    return module, guard


@pytest.mark.asyncio
async def test_denies_when_no_investor_profile_exists():
    _, guard = await _build_guard_and_repos()
    request = make_request()
    request.state.user = {"sub": "1", "role": "INVESTOR"}
    context = ExecutionContext(request, object, None)

    with pytest.raises(ForbiddenException):
        await guard.can_activate(context)


@pytest.mark.asyncio
async def test_denies_when_kyc_status_is_pending():
    module, guard = await _build_guard_and_repos()
    from austial.orm import repository_token

    users = module.get(repository_token(User))
    investors = module.get(repository_token(InvestorProfile))
    # `# type: ignore[call-arg]` -- see the note on `User(...)` in `AuthService.register()`
    # (`src/modules/auth/auth_service.py`): `austial-py` ships no `py.typed` marker yet.
    user = await users.save(User(email="pending@example.com", password_hash="x", role="INVESTOR"))  # type: ignore[call-arg]
    await investors.save(InvestorProfile(user=user, kyc_status="PENDING"))  # type: ignore[call-arg]

    request = make_request()
    request.state.user = {"sub": str(user.id), "role": "INVESTOR"}
    context = ExecutionContext(request, object, None)

    with pytest.raises(ForbiddenException):
        await guard.can_activate(context)


@pytest.mark.asyncio
async def test_allows_when_kyc_status_is_verified():
    module, guard = await _build_guard_and_repos()
    from austial.orm import repository_token

    users = module.get(repository_token(User))
    investors = module.get(repository_token(InvestorProfile))
    # See the `# type: ignore[call-arg]` note above (`austial-py` `py.typed` gap).
    user = await users.save(User(email="verified@example.com", password_hash="x", role="INVESTOR"))  # type: ignore[call-arg]
    await investors.save(InvestorProfile(user=user, kyc_status="VERIFIED"))  # type: ignore[call-arg]

    request = make_request()
    request.state.user = {"sub": str(user.id), "role": "INVESTOR"}
    context = ExecutionContext(request, object, None)

    assert await guard.can_activate(context) is True


@pytest.mark.asyncio
async def test_denies_when_no_authenticated_user():
    _, guard = await _build_guard_and_repos()
    request = make_request()
    context = ExecutionContext(request, object, None)

    with pytest.raises(ForbiddenException):
        await guard.can_activate(context)
