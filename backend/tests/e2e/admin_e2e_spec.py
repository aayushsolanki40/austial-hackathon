"""End-to-end tests for the admin module (Phase 1.10) -- registers/logs in
users through the real ``/auth`` flow, promotes one to ``ADMIN`` directly via
its repository (``/auth/register`` always creates an ``INVESTOR``, there's no
public self-promotion route -- by design), then exercises every
``/admin/...`` route, mirroring ``auth_e2e_spec.py``'s pattern.
"""

from __future__ import annotations

import pytest
from austial.config import ConfigService
from austial.orm import DataSource, OrmModule, repository_token
from austial.testing import Test
from httpx import ASGITransport, AsyncClient

from src.app_controller import AppController
from src.app_service import AppService
from src.modules.admin.admin_module import AdminModule
from src.modules.auth.auth_module import AuthModule
from src.modules.auth.entities.refresh_token import RefreshToken
from src.modules.auth.entities.user import User
from src.modules.compliance.compliance_module import ComplianceModule
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.investors.entities.investor_profile import InvestorProfile


def _config_service() -> ConfigService:
    return ConfigService({"JWT_SECRET": "admin-e2e-test-secret"})


async def _build_app_and_module():
    orm_module = OrmModule.for_root(
        type_="sqlite",
        url="sqlite+aiosqlite:///:memory:",
        entities=[User, RefreshToken, InvestorProfile, AuditLog],
        synchronize=True,
    )
    module = await Test.create_testing_module(
        imports=[orm_module, AuthModule, AdminModule, ComplianceModule],
        controllers=[AppController],
        providers=[AppService, {"provide": ConfigService, "useValue": _config_service()}],
    ).compile()
    await module.get(DataSource).initialize()
    app = module.create_austial_application()
    await app.init()
    return app, module


async def _register_and_login(client: AsyncClient, *, email: str, password: str = "password123") -> str:
    await client.post("/auth/register", json={"email": email, "password": password})
    login_response = await client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 201
    return login_response.json()["tokens"]["access_token"]


async def _promote_to_admin(module, *, email: str) -> None:
    users = module.get(repository_token(User))
    user = await users.find_one_by({"email": email})
    user.role = "ADMIN"
    await users.save(user)


@pytest.mark.asyncio
async def test_non_admin_is_forbidden_from_every_admin_route():
    app, _ = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        token = await _register_and_login(client, email="plain-investor@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        assert (await client.get("/admin/dashboard/summary", headers=headers)).status_code == 403
        assert (await client.get("/admin/users", headers=headers)).status_code == 403
        assert (await client.patch("/admin/users/1/role", headers=headers, json={"role": "ADMIN"})).status_code == 403
        assert (await client.patch("/admin/users/1/suspend", headers=headers)).status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_request_is_rejected():
    app, _ = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/admin/dashboard/summary")

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_dashboard_summary_reflects_seeded_data():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _register_and_login(client, email="investor-a@example.com")
        admin_token = await _register_and_login(client, email="admin@example.com")
        await _promote_to_admin(module, email="admin@example.com")
        # Re-login so the JWT's `role` claim reflects the promotion (claims are
        # baked in at issue time, see `AuthService._encode`).
        admin_token = await _register_and_login(client, email="admin@example.com")
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = await client.get("/admin/dashboard/summary", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["users_by_role"]["INVESTOR"] == 1
        assert body["users_by_role"]["ADMIN"] == 1
        # No `InvestorProfile` rows seeded in this flow (only auth registration) -- both stay 0.
        assert body["investor_count"] == 0
        assert body["pending_kyc_count"] == 0


@pytest.mark.asyncio
async def test_admin_list_users_search_and_role_update_and_suspend_flow():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _register_and_login(client, email="target-user@example.com")
        await _promote_to_admin(module, email="target-user@example.com")
        admin_token = await _register_and_login(client, email="target-user@example.com")
        headers = {"Authorization": f"Bearer {admin_token}"}

        users = module.get(repository_token(User))
        target = await users.find_one_by({"email": "target-user@example.com"})

        list_response = await client.get("/admin/users", headers=headers, params={"search": "target-user"})
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1
        assert list_response.json()["items"][0]["email"] == "target-user@example.com"

        role_response = await client.patch(
            f"/admin/users/{target.id}/role", headers=headers, json={"role": "COMPLIANCE_OFFICER"}
        )
        assert role_response.status_code == 200
        assert role_response.json()["role"] == "COMPLIANCE_OFFICER"

        suspend_response = await client.patch(f"/admin/users/{target.id}/suspend", headers=headers)
        assert suspend_response.status_code == 200
        assert suspend_response.json()["is_active"] is False

        audit_logs = module.get(repository_token(AuditLog))
        actions = [log.action for log in await audit_logs.find()]
        assert "admin.user.role_changed" in actions
        assert "admin.user.suspended" in actions


@pytest.mark.asyncio
async def test_admin_role_update_rejects_unknown_role_with_400():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _register_and_login(client, email="admin2@example.com")
        await _promote_to_admin(module, email="admin2@example.com")
        admin_token = await _register_and_login(client, email="admin2@example.com")
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = await client.patch("/admin/users/1/role", headers=headers, json={"role": "NOT_A_REAL_ROLE"})

        # `ValidationPipe`/FastAPI request-body validation failures surface as `BadRequestException`
        # (400) in this framework's convention, not FastAPI's own default 422 -- see
        # `AustialApplication._install_fallback_exception_handlers`.
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_suspended_user_cannot_log_in():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await _register_and_login(client, email="will-be-suspended@example.com")
        await _register_and_login(client, email="admin3@example.com")
        await _promote_to_admin(module, email="admin3@example.com")
        admin_token = await _register_and_login(client, email="admin3@example.com")
        headers = {"Authorization": f"Bearer {admin_token}"}

        users = module.get(repository_token(User))
        target = await users.find_one_by({"email": "will-be-suspended@example.com"})
        await client.patch(f"/admin/users/{target.id}/suspend", headers=headers)

        login_response = await client.post(
            "/auth/login", json={"email": "will-be-suspended@example.com", "password": "password123"}
        )

        assert login_response.status_code == 401
