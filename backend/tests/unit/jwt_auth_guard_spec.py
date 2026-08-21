"""Unit tests for ``JwtAuthGuard`` -- Phase 1.3."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from austial import ExecutionContext, UnauthorizedException
from austial.config import ConfigService
from jose import jwt

from src.modules.auth.auth_constants import ACCESS_TOKEN_TYPE, JWT_ALGORITHM, REFRESH_TOKEN_TYPE
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from tests.unit._request_factory import make_request

_SECRET = "guard-unit-test-secret"


def _config() -> ConfigService:
    return ConfigService({"JWT_SECRET": _SECRET})


def _make_token(token_type: str = ACCESS_TOKEN_TYPE, *, expired: bool = False) -> str:
    now = datetime.now(UTC)
    exp = now - timedelta(minutes=1) if expired else now + timedelta(minutes=15)
    payload = {"sub": "1", "email": "a@example.com", "role": "INVESTOR", "type": token_type, "iat": now, "exp": exp}
    return jwt.encode(payload, _SECRET, algorithm=JWT_ALGORITHM)


@pytest.mark.asyncio
async def test_allows_valid_access_token_and_attaches_claims():
    guard = JwtAuthGuard(_config())
    token = _make_token()
    request = make_request(headers={"authorization": f"Bearer {token}"})
    context = ExecutionContext(request, object, None)

    allowed = await guard.can_activate(context)

    assert allowed is True
    assert request.state.user["sub"] == "1"
    assert request.state.user["role"] == "INVESTOR"


@pytest.mark.asyncio
async def test_rejects_missing_authorization_header():
    guard = JwtAuthGuard(_config())
    request = make_request()
    context = ExecutionContext(request, object, None)

    with pytest.raises(UnauthorizedException):
        await guard.can_activate(context)


@pytest.mark.asyncio
async def test_rejects_malformed_token():
    guard = JwtAuthGuard(_config())
    request = make_request(headers={"authorization": "Bearer not-a-real-jwt"})
    context = ExecutionContext(request, object, None)

    with pytest.raises(UnauthorizedException):
        await guard.can_activate(context)


@pytest.mark.asyncio
async def test_rejects_expired_token():
    guard = JwtAuthGuard(_config())
    token = _make_token(expired=True)
    request = make_request(headers={"authorization": f"Bearer {token}"})
    context = ExecutionContext(request, object, None)

    with pytest.raises(UnauthorizedException):
        await guard.can_activate(context)


@pytest.mark.asyncio
async def test_rejects_refresh_token_presented_as_access_token():
    guard = JwtAuthGuard(_config())
    token = _make_token(token_type=REFRESH_TOKEN_TYPE)
    request = make_request(headers={"authorization": f"Bearer {token}"})
    context = ExecutionContext(request, object, None)

    with pytest.raises(UnauthorizedException):
        await guard.can_activate(context)
