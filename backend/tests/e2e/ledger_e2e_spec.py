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
from src.modules.investors.entities.wallet_mapping import WalletMapping
from src.modules.investors.investors_module import InvestorsModule
from src.modules.ledger.entities.funding_instruction import FundingInstruction
from src.modules.ledger.entities.ledger_account import LedgerAccount
from src.modules.ledger.entities.ledger_entry import LedgerEntry
from src.modules.ledger.entities.payout_instruction import PayoutInstruction
from src.modules.ledger.ledger_module import LedgerModule


def _config_service() -> ConfigService:
    return ConfigService(
        {
            "JWT_SECRET": "ledger-e2e-test-secret",
            "LEDGER_BENEFICIARY_NAME": "Austial GIFT City IBU Client Settlement Account",
            "LEDGER_BENEFICIARY_BANK_NAME": "Test Bank",
            "LEDGER_BENEFICIARY_ACCOUNT_NUMBER": "000123456789",
            "LEDGER_BENEFICIARY_SWIFT_BIC": "TESTINBBXXX",
        }
    )


async def _build_app_and_module():
    orm_module = OrmModule.for_root(
        type_="sqlite",
        url="sqlite+aiosqlite:///:memory:",
        entities=[
            User,
            RefreshToken,
            InvestorProfile,
            WalletMapping,
            AuditLog,
            LedgerAccount,
            LedgerEntry,
            FundingInstruction,
            PayoutInstruction,
        ],
        synchronize=True,
    )
    module = await Test.create_testing_module(
        imports=[orm_module, AuthModule, InvestorsModule, LedgerModule, ComplianceModule],
        controllers=[AppController],
        providers=[AppService, {"provide": ConfigService, "useValue": _config_service()}],
    ).compile()
    await module.get(DataSource).initialize()
    app = module.create_austial_application()
    app.use_global_interceptors(AuditInterceptor)
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


async def _create_investor(client: AsyncClient, module, *, email: str) -> dict[str, str]:
    headers = await _login_as(client, module, email=email, role="INVESTOR")
    profile_response = await client.post(
        "/investors/profile",
        headers=headers,
        json={"investor_type": "INDIVIDUAL", "jurisdiction": "in", "risk_profile": "MODERATE"},
    )
    assert profile_response.status_code == 201
    return headers


@pytest.mark.asyncio
async def test_funding_confirmation_credits_the_investors_account():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        officer_headers = await _login_as(client, module, email="officer@example.com", role="COMPLIANCE_OFFICER")
        investor_headers = await _create_investor(client, module, email="investor@example.com")

        account_response = await client.get("/ledger/account", headers=investor_headers)
        assert account_response.status_code == 200
        assert account_response.json()["available_balance"] == 0

        funding_response = await client.post(
            "/ledger/funding-instructions", headers=investor_headers, json={"amount": 2500, "currency": "USD"}
        )
        assert funding_response.status_code == 201
        funding = funding_response.json()
        assert funding["status"] == "PENDING"
        assert funding["reference_code"].startswith("FUND-")
        assert funding["beneficiary_swift_bic"] == "TESTINBBXXX"
        instruction_id = funding["id"]

        # ★ Role separation: an investor cannot confirm their own funding instruction.
        forbidden_response = await client.post(
            f"/ledger/funding-instructions/{instruction_id}/confirm", headers=investor_headers, json={}
        )
        assert forbidden_response.status_code == 403

        confirm_response = await client.post(
            f"/ledger/funding-instructions/{instruction_id}/confirm", headers=officer_headers, json={}
        )
        assert confirm_response.status_code == 201
        assert confirm_response.json()["status"] == "CONFIRMED"

        credited_account = await client.get("/ledger/account", headers=investor_headers)
        assert credited_account.json()["available_balance"] == 2500

        entries_response = await client.get("/ledger/entries", headers=investor_headers)
        assert entries_response.status_code == 200
        entries = entries_response.json()
        assert entries["total"] == 1
        assert entries["items"][0]["entry_type"] == "CREDIT_FUNDING"
        assert entries["items"][0]["balance_after"] == 2500

        # ★ Idempotency: re-confirming the same (now-``CONFIRMED``) instruction is refused, and
        # the account is not double-credited.
        repeat_confirm = await client.post(
            f"/ledger/funding-instructions/{instruction_id}/confirm", headers=officer_headers, json={}
        )
        assert repeat_confirm.status_code == 409
        unchanged_account = await client.get("/ledger/account", headers=investor_headers)
        assert unchanged_account.json()["available_balance"] == 2500


@pytest.mark.asyncio
async def test_currency_validation_rejects_inr_at_the_dto_layer():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        investor_headers = await _create_investor(client, module, email="investor-inr@example.com")

        response = await client.post(
            "/ledger/funding-instructions", headers=investor_headers, json={"amount": 100, "currency": "INR"}
        )
        # `ValidationPipe`/FastAPI request-body validation failures surface as `BadRequestException`
        # (400) in this framework's convention, not FastAPI's own default 422 -- see
        # `AustialApplication._install_fallback_exception_handlers` (mirrors
        # `admin_e2e_spec.py::test_admin_role_update_rejects_unknown_role_with_400`).
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_payout_instruction_debits_the_account():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        officer_headers = await _login_as(client, module, email="officer2@example.com", role="COMPLIANCE_OFFICER")
        investor_headers = await _create_investor(client, module, email="investor2@example.com")

        funding_response = await client.post(
            "/ledger/funding-instructions", headers=investor_headers, json={"amount": 1000, "currency": "USD"}
        )
        instruction_id = funding_response.json()["id"]
        await client.post(f"/ledger/funding-instructions/{instruction_id}/confirm", headers=officer_headers, json={})

        investors = module.get(repository_token(InvestorProfile))
        investor = (await investors.find())[0]

        payout_response = await client.post(
            "/ledger/payout-instructions",
            headers=officer_headers,
            json={
                "investor_id": investor.id,
                "amount": 300,
                "currency": "USD",
                "memo": "Redemption payout",
                "idempotency_key": "payout-e2e-001",
            },
        )
        assert payout_response.status_code == 201
        assert payout_response.json()["status"] == "RECORDED"

        account_response = await client.get("/ledger/account", headers=investor_headers)
        assert account_response.json()["available_balance"] == 700

        # An investor cannot record a payout themselves.
        forbidden_response = await client.post(
            "/ledger/payout-instructions",
            headers=investor_headers,
            json={"investor_id": investor.id, "amount": 10, "currency": "USD", "idempotency_key": "should-fail"},
        )
        assert forbidden_response.status_code == 403


@pytest.mark.asyncio
async def test_compliance_officer_can_list_pending_funding_instructions():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        officer_headers = await _login_as(client, module, email="officer3@example.com", role="COMPLIANCE_OFFICER")
        investor_headers = await _create_investor(client, module, email="investor3@example.com")
        await client.post(
            "/ledger/funding-instructions", headers=investor_headers, json={"amount": 500, "currency": "USD"}
        )

        list_response = await client.get(
            "/ledger/funding-instructions", headers=officer_headers, params={"status": "PENDING"}
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1

    audit_logs = module.get(repository_token(AuditLog))
    _ = audit_logs  # AuditInterceptor coverage is asserted elsewhere (issuance_e2e_spec.py)
