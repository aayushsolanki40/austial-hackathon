"""End-to-end tests for the auth flow (``POST /auth/register`` -> ``login`` ->
``refresh`` -> ``logout``) and, since ``AuditInterceptor`` (Phase 1.6) is
wired globally in ``src/main.py``, verifies every mutating request along the
way produces an ``AuditLog`` row while a plain ``GET`` does not.
"""

from __future__ import annotations

import pytest
from austial.config import ConfigService
from austial.orm import DataSource, OrmModule, repository_token
from austial.testing import Test
from httpx import ASGITransport, AsyncClient

from src.app_controller import AppController
from src.app_service import AppService
from src.modules.auth.auth_module import AuthModule
from src.modules.auth.entities.refresh_token import RefreshToken
from src.modules.auth.entities.user import User
from src.modules.compliance.compliance_module import ComplianceModule
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.compliance.interceptors.audit_interceptor import AuditInterceptor
from src.modules.investors.entities.investor_profile import InvestorProfile


def _config_service() -> ConfigService:
    return ConfigService({"JWT_SECRET": "e2e-test-secret"})


async def _build_app_and_module():
    orm_module = OrmModule.for_root(
        type_="sqlite",
        url="sqlite+aiosqlite:///:memory:",
        entities=[User, RefreshToken, InvestorProfile, AuditLog],
        synchronize=True,
    )
    module = await Test.create_testing_module(
        imports=[orm_module, AuthModule, ComplianceModule],
        controllers=[AppController],
        providers=[AppService, {"provide": ConfigService, "useValue": _config_service()}],
    ).compile()
    await module.get(DataSource).initialize()
    app = module.create_austial_application()
    app.use_global_interceptors(AuditInterceptor)
    await app.init()
    return app, module


@pytest.mark.asyncio
async def test_register_login_refresh_logout_flow_writes_audit_logs():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        register_response = await client.post(
            "/auth/register", json={"email": "e2e@example.com", "password": "password123"}
        )
        assert register_response.status_code == 201
        register_body = register_response.json()
        assert register_body["user"]["email"] == "e2e@example.com"
        refresh_token = register_body["tokens"]["refresh_token"]

        login_response = await client.post("/auth/login", json={"email": "e2e@example.com", "password": "password123"})
        assert login_response.status_code == 201

        refresh_response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_response.status_code == 201
        new_refresh_token = refresh_response.json()["refresh_token"]

        logout_response = await client.post("/auth/logout", json={"refresh_token": new_refresh_token})
        assert logout_response.status_code == 201

        root_response = await client.get("/")
        assert root_response.status_code == 200

    audit_logs_repo = module.get(repository_token(AuditLog))
    all_logs = await audit_logs_repo.find()
    logged_actions = [log.action for log in all_logs]

    assert any("POST /auth/register" in action for action in logged_actions)
    assert any("POST /auth/login" in action for action in logged_actions)
    assert any("POST /auth/refresh" in action for action in logged_actions)
    assert any("POST /auth/logout" in action for action in logged_actions)
    # A plain GET must not produce an audit row.
    assert not any("GET /" in action for action in logged_actions)


@pytest.mark.asyncio
async def test_register_endpoint_rejects_duplicate_email():
    app, _ = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.post("/auth/register", json={"email": "dup@example.com", "password": "password123"})
        second = await client.post("/auth/register", json={"email": "dup@example.com", "password": "password123"})

        assert second.status_code == 409


@pytest.mark.asyncio
async def test_login_endpoint_rejects_invalid_credentials():
    app, _ = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong"})

        assert response.status_code == 401
