"""Unit tests for ``AuthService`` -- Phase 1.2. register/login/refresh/logout,
built straight from the DI container against an in-memory SQLite
``DataSource``, mirroring ``health_service_spec.py``'s pattern.
"""

from __future__ import annotations

import pytest
from austial import ConflictException, UnauthorizedException
from austial.config import ConfigService
from austial.orm import DataSource, OrmModule
from austial.testing import Test

from src.modules.auth.auth_dto import LoginDto, LogoutDto, RefreshDto, RegisterDto
from src.modules.auth.auth_service import AuthService
from src.modules.auth.entities.refresh_token import RefreshToken
from src.modules.auth.entities.user import User


def _config_service() -> ConfigService:
    return ConfigService(
        {
            "JWT_SECRET": "unit-test-secret",
            "JWT_ACCESS_TOKEN_TTL_MINUTES": "15",
            "JWT_REFRESH_TOKEN_TTL_DAYS": "30",
        }
    )


async def _build_service() -> AuthService:
    module = await Test.create_testing_module(
        imports=[
            OrmModule.for_root(
                type_="sqlite",
                url="sqlite+aiosqlite:///:memory:",
                entities=[User, RefreshToken],
                synchronize=True,
            ),
            OrmModule.for_feature([User, RefreshToken]),
        ],
        providers=[AuthService, {"provide": ConfigService, "useValue": _config_service()}],
    ).compile()
    await module.get(DataSource).initialize()
    return module.get(AuthService)


@pytest.mark.asyncio
async def test_register_creates_user_and_returns_token_pair():
    service = await _build_service()

    result = await service.register(RegisterDto(email="investor@example.com", password="password123"))

    assert result.user.email == "investor@example.com"
    assert result.user.role == "INVESTOR"
    assert result.tokens.access_token
    assert result.tokens.refresh_token
    assert result.tokens.token_type == "bearer"


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email():
    service = await _build_service()
    await service.register(RegisterDto(email="dup@example.com", password="password123"))

    with pytest.raises(ConflictException):
        await service.register(RegisterDto(email="dup@example.com", password="password123"))


@pytest.mark.asyncio
async def test_login_succeeds_with_correct_credentials():
    service = await _build_service()
    await service.register(RegisterDto(email="login@example.com", password="password123"))

    result = await service.login(LoginDto(email="login@example.com", password="password123"))

    assert result.user.email == "login@example.com"
    assert result.tokens.access_token


@pytest.mark.asyncio
async def test_login_rejects_wrong_password():
    service = await _build_service()
    await service.register(RegisterDto(email="wrongpw@example.com", password="password123"))

    with pytest.raises(UnauthorizedException):
        await service.login(LoginDto(email="wrongpw@example.com", password="not-the-password"))


@pytest.mark.asyncio
async def test_login_rejects_unknown_email():
    service = await _build_service()

    with pytest.raises(UnauthorizedException):
        await service.login(LoginDto(email="nobody@example.com", password="password123"))


@pytest.mark.asyncio
async def test_refresh_rotates_token_and_revokes_old_one():
    service = await _build_service()
    registered = await service.register(RegisterDto(email="refresh@example.com", password="password123"))
    old_refresh_token = registered.tokens.refresh_token

    rotated = await service.refresh(RefreshDto(refresh_token=old_refresh_token))

    assert rotated.access_token
    assert rotated.refresh_token != old_refresh_token

    # The old refresh token was single-use -- rotating it again must fail.
    with pytest.raises(UnauthorizedException):
        await service.refresh(RefreshDto(refresh_token=old_refresh_token))


@pytest.mark.asyncio
async def test_refresh_rejects_garbage_token():
    service = await _build_service()

    with pytest.raises(UnauthorizedException):
        await service.refresh(RefreshDto(refresh_token="not-a-real-jwt"))


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token_idempotently():
    service = await _build_service()
    registered = await service.register(RegisterDto(email="logout@example.com", password="password123"))
    refresh_token = registered.tokens.refresh_token

    first = await service.logout(LogoutDto(refresh_token=refresh_token))
    assert first.message

    # Logging out again with the same (now-revoked) token is a no-op, not an error.
    second = await service.logout(LogoutDto(refresh_token=refresh_token))
    assert second.message

    with pytest.raises(UnauthorizedException):
        await service.refresh(RefreshDto(refresh_token=refresh_token))
