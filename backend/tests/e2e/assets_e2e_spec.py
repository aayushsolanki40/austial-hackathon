"""End-to-end tests for the Phase 3 issuer/custodian/asset flow -- proves the exit criteria
from the build plan: register as an ``ISSUER`` -> create issuer profile -> submit an asset ->
a ``COMPLIANCE_OFFICER`` registers and IFSCA-verifies a custodian -> the issuer attaches that
custodian to their asset -> ``tokenization_ready`` flips to ``True``. Also proves the ★
regulatory rule end-to-end over HTTP: attaching an *unverified* custodian is rejected with a 409.
Mirrors ``kyc_e2e_spec.py``'s pattern (real ``/auth`` flow + direct-repository role promotion).
"""

from __future__ import annotations

import pytest
from austial.config import ConfigService
from austial.orm import DataSource, OrmModule, repository_token
from austial.testing import Test
from httpx import ASGITransport, AsyncClient

from src.app_controller import AppController
from src.app_service import AppService
from src.modules.assets.assets_module import AssetsModule
from src.modules.assets.entities.asset import Asset
from src.modules.auth.auth_module import AuthModule
from src.modules.auth.entities.refresh_token import RefreshToken
from src.modules.auth.entities.user import User
from src.modules.compliance.compliance_module import ComplianceModule
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.custodians.custodians_module import CustodiansModule
from src.modules.custodians.entities.custodian import Custodian
from src.modules.issuers.entities.issuer import Issuer
from src.modules.issuers.issuers_module import IssuersModule


def _config_service() -> ConfigService:
    return ConfigService({"JWT_SECRET": "assets-e2e-test-secret"})


async def _build_app_and_module():
    orm_module = OrmModule.for_root(
        type_="sqlite",
        url="sqlite+aiosqlite:///:memory:",
        entities=[User, RefreshToken, Issuer, Custodian, Asset, AuditLog],
        synchronize=True,
    )
    module = await Test.create_testing_module(
        imports=[orm_module, AuthModule, IssuersModule, CustodiansModule, AssetsModule, ComplianceModule],
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


async def _promote_role(module, *, email: str, role: str) -> None:
    users = module.get(repository_token(User))
    user = await users.find_one_by({"email": email})
    user.role = role
    await users.save(user)


async def _login_as(client: AsyncClient, module, *, email: str, role: str) -> dict[str, str]:
    await _register_and_login(client, email=email)
    await _promote_role(module, email=email, role=role)
    token = await _register_and_login(client, email=email)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_full_asset_tokenization_readiness_flow():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        issuer_headers = await _login_as(client, module, email="issuer@example.com", role="ISSUER")

        profile_response = await client.post(
            "/issuers/profile",
            headers=issuer_headers,
            json={
                "legal_name": "Acme Real Estate Ltd",
                "registration_number": "RE-12345",
                "registration_jurisdiction": "in",
            },
        )
        assert profile_response.status_code == 201
        assert profile_response.json()["verification_status"] == "PENDING"

        asset_response = await client.post(
            "/assets",
            headers=issuer_headers,
            json={"name": "Tower A - Floor 12", "asset_class": "REAL_ESTATE", "description": "Prime commercial floor"},
        )
        assert asset_response.status_code == 201
        asset = asset_response.json()
        assert asset["tokenization_ready"] is False
        assert asset["custodian_id"] is None
        asset_id = asset["id"]

        officer_headers = await _login_as(client, module, email="officer@example.com", role="COMPLIANCE_OFFICER")

        custodian_response = await client.post(
            "/custodians",
            headers=officer_headers,
            json={"name": "GIFT City Custody Services Ltd", "ifsca_registration_no": "IFSCA-CUST-001"},
        )
        assert custodian_response.status_code == 201
        custodian = custodian_response.json()
        assert custodian["ifsca_verified"] is False
        custodian_id = custodian["id"]

        # Attaching an unverified custodian is rejected -- the ★ regulatory rule, over HTTP.
        premature_attach = await client.post(
            f"/assets/{asset_id}/custodian", headers=issuer_headers, json={"custodian_id": custodian_id}
        )
        assert premature_attach.status_code == 409

        verify_response = await client.post(f"/custodians/{custodian_id}/verify", headers=officer_headers)
        assert verify_response.status_code == 201
        assert verify_response.json()["ifsca_verified"] is True

        attach_response = await client.post(
            f"/assets/{asset_id}/custodian", headers=issuer_headers, json={"custodian_id": custodian_id}
        )
        assert attach_response.status_code == 201
        attached = attach_response.json()
        assert attached["custodian_id"] == custodian_id
        assert attached["custodian_verified"] is True
        assert attached["tokenization_ready"] is True

        get_response = await client.get(f"/assets/{asset_id}", headers=issuer_headers)
        assert get_response.json()["tokenization_ready"] is True


@pytest.mark.asyncio
async def test_investor_cannot_submit_assets_and_issuer_cannot_verify_custodians():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        investor_token = await _register_and_login(client, email="investor@example.com")
        investor_headers = {"Authorization": f"Bearer {investor_token}"}
        assert (
            await client.post("/assets", headers=investor_headers, json={"name": "X", "asset_class": "SECURITY"})
        ).status_code == 403

        issuer_headers = await _login_as(client, module, email="issuer2@example.com", role="ISSUER")
        await client.post(
            "/issuers/profile",
            headers=issuer_headers,
            json={"legal_name": "Other Ltd", "registration_number": "RE-99", "registration_jurisdiction": "IN"},
        )
        # Issuers can read the custodian registry (to pick one to attach)...
        assert (await client.get("/custodians", headers=issuer_headers)).status_code == 200
        # ...but cannot create or verify custodians.
        assert (
            await client.post("/custodians", headers=issuer_headers, json={"name": "X", "ifsca_registration_no": "Y"})
        ).status_code == 403


@pytest.mark.asyncio
async def test_a_custodian_cannot_be_attached_twice():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        issuer_headers = await _login_as(client, module, email="issuer3@example.com", role="ISSUER")
        await client.post(
            "/issuers/profile",
            headers=issuer_headers,
            json={"legal_name": "Third Ltd", "registration_number": "RE-77", "registration_jurisdiction": "IN"},
        )
        asset_id = (
            await client.post("/assets", headers=issuer_headers, json={"name": "Bond A", "asset_class": "SECURITY"})
        ).json()["id"]

        officer_headers = await _login_as(client, module, email="officer2@example.com", role="COMPLIANCE_OFFICER")
        custodian_dto = {"name": "Custody Co", "ifsca_registration_no": "IFSCA-999"}
        custodian_id = (await client.post("/custodians", headers=officer_headers, json=custodian_dto)).json()["id"]
        await client.post(f"/custodians/{custodian_id}/verify", headers=officer_headers)

        first_attach = await client.post(
            f"/assets/{asset_id}/custodian", headers=issuer_headers, json={"custodian_id": custodian_id}
        )
        assert first_attach.status_code == 201

        second_attach = await client.post(
            f"/assets/{asset_id}/custodian", headers=issuer_headers, json={"custodian_id": custodian_id}
        )
        assert second_attach.status_code == 409
