"""End-to-end tests for the Phase 4 issuance workflow -- proves the exit criteria from the
build plan over real HTTP: register as ``ISSUER`` -> create issuer profile -> submit a
tokenization-ready asset (custodian attached + IFSCA-verified, per Phase 3) -> create a
tokenization proposal -> walk it through the full state machine as a ``COMPLIANCE_OFFICER`` ->
upload all six disclosure types -> ``launch`` creates a ``TokenSeries`` and flips the proposal to
``LAUNCHED``. Also proves the ★ headline disclosure-completeness gate blocks ``launch`` with a 422
when even one disclosure type is missing, and exercises the token-series circuit breaker.
Mirrors ``assets_e2e_spec.py``'s/``kyc_e2e_spec.py``'s pattern (real ``/auth`` flow + direct-
repository role promotion, moto-mocked S3 for the presigned upload-url endpoints).
"""

from __future__ import annotations

import boto3
import pytest
from austial.config import ConfigService
from austial.orm import DataSource, OrmModule, repository_token
from austial.testing import Test
from httpx import ASGITransport, AsyncClient
from moto import mock_aws

from src.app_controller import AppController
from src.app_service import AppService
from src.modules.assets.assets_module import AssetsModule
from src.modules.assets.entities.asset import Asset
from src.modules.auth.auth_module import AuthModule
from src.modules.auth.entities.refresh_token import RefreshToken
from src.modules.auth.entities.user import User
from src.modules.compliance.compliance_module import ComplianceModule
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.compliance.interceptors.audit_interceptor import AuditInterceptor
from src.modules.custodians.custodians_module import CustodiansModule
from src.modules.custodians.entities.custodian import Custodian
from src.modules.issuance.entities.disclosure_document import DISCLOSURE_TYPES, DisclosureDocument
from src.modules.issuance.entities.smart_contract_deployment import SmartContractDeployment
from src.modules.issuance.entities.token_series import TokenSeries
from src.modules.issuance.entities.tokenization_proposal import TokenizationProposal
from src.modules.issuance.issuance_module import IssuanceModule
from src.modules.issuers.entities.issuer import Issuer
from src.modules.issuers.issuers_module import IssuersModule

_BUCKET = "swadely-documents-issuance-e2e-test"
_REGION = "us-east-1"


def _config_service() -> ConfigService:
    return ConfigService(
        {"JWT_SECRET": "issuance-e2e-test-secret", "DOCUMENTS_S3_BUCKET": _BUCKET, "AWS_REGION": _REGION}
    )


@pytest.fixture(autouse=True)
def _hermetic_infra():
    # No live AWS (`moto`'s `mock_aws`, mirrors `kyc_e2e_spec.py`) -- `IssuanceService.
    # get_disclosure_upload_url` generates a real S3 presigned URL.
    with mock_aws():
        client = boto3.client("s3", region_name=_REGION)
        client.create_bucket(Bucket=_BUCKET)
        yield


async def _build_app_and_module():
    orm_module = OrmModule.for_root(
        type_="sqlite",
        url="sqlite+aiosqlite:///:memory:",
        entities=[
            User,
            RefreshToken,
            Issuer,
            Custodian,
            Asset,
            TokenizationProposal,
            DisclosureDocument,
            TokenSeries,
            SmartContractDeployment,
            AuditLog,
        ],
        synchronize=True,
    )
    module = await Test.create_testing_module(
        imports=[
            orm_module,
            AuthModule,
            IssuersModule,
            CustodiansModule,
            AssetsModule,
            IssuanceModule,
            ComplianceModule,
        ],
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


async def _create_tokenization_ready_asset(
    client: AsyncClient, module, *, issuer_email: str, officer_headers: dict[str, str], registration_no: str
) -> tuple[dict[str, str], int]:
    """Registers an issuer, submits an asset, and attaches an IFSCA-verified custodian to it --
    i.e. drives it through the whole of Phase 3 so it clears the ★ tokenization-readiness gate
    this phase's ``create_proposal`` re-checks. Returns the issuer's auth headers and the asset id.
    """
    issuer_headers = await _login_as(client, module, email=issuer_email, role="ISSUER")
    await client.post(
        "/issuers/profile",
        headers=issuer_headers,
        json={
            "legal_name": "Acme Real Estate Ltd",
            "registration_number": "RE-12345",
            "registration_jurisdiction": "in",
        },
    )
    asset_response = await client.post(
        "/assets",
        headers=issuer_headers,
        json={"name": "Tower A - Floor 12", "asset_class": "REAL_ESTATE", "description": "Prime commercial floor"},
    )
    assert asset_response.status_code == 201
    asset_id = asset_response.json()["id"]

    custodian_response = await client.post(
        "/custodians",
        headers=officer_headers,
        json={"name": "GIFT City Custody Services Ltd", "ifsca_registration_no": registration_no},
    )
    custodian_id = custodian_response.json()["id"]
    await client.post(f"/custodians/{custodian_id}/verify", headers=officer_headers)

    attach_response = await client.post(
        f"/assets/{asset_id}/custodian", headers=issuer_headers, json={"custodian_id": custodian_id}
    )
    assert attach_response.status_code == 201
    assert attach_response.json()["tokenization_ready"] is True
    return issuer_headers, asset_id


def _proposal_body(asset_id: int) -> dict:
    return {
        "asset_id": asset_id,
        "total_units": 1000,
        "unit_price_usd": 100,
        "min_subscription_units": 10,
        "subscription_start_at": "2026-09-01T00:00:00",
        "subscription_end_at": "2026-10-01T00:00:00",
    }


async def _upload_disclosure(client, issuer_headers, proposal_id, disclosure_type) -> None:
    upload_url_response = await client.post(
        f"/issuance/proposals/mine/{proposal_id}/disclosures/upload-url",
        headers=issuer_headers,
        json={"disclosure_type": disclosure_type, "content_type": "application/pdf"},
    )
    assert upload_url_response.status_code == 201
    object_key = upload_url_response.json()["object_key"]
    add_response = await client.post(
        f"/issuance/proposals/mine/{proposal_id}/disclosures",
        headers=issuer_headers,
        json={"disclosure_type": disclosure_type, "object_key": object_key},
    )
    assert add_response.status_code == 201


@pytest.mark.asyncio
async def test_full_issuance_pipeline_reaches_launched_with_all_disclosures():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        officer_headers = await _login_as(client, module, email="officer@example.com", role="COMPLIANCE_OFFICER")
        issuer_headers, asset_id = await _create_tokenization_ready_asset(
            client,
            module,
            issuer_email="issuer@example.com",
            officer_headers=officer_headers,
            registration_no="IFSCA-CUST-E2E-1",
        )

        proposal_response = await client.post(
            "/issuance/proposals", headers=issuer_headers, json=_proposal_body(asset_id)
        )
        assert proposal_response.status_code == 201
        proposal = proposal_response.json()
        assert proposal["status"] == "DRAFT"
        assert proposal["disclosures_complete"] is False
        proposal_id = proposal["id"]

        submit_response = await client.post(
            f"/issuance/proposals/mine/{proposal_id}/submit", headers=issuer_headers
        )
        assert submit_response.status_code == 201
        assert submit_response.json()["status"] == "DOCUMENTATION_REVIEW"

        approve_response = await client.post(
            f"/issuance/proposals/{proposal_id}/compliance-approve", headers=officer_headers
        )
        assert approve_response.status_code == 201
        assert approve_response.json()["status"] == "COMPLIANCE_APPROVED"

        file_response = await client.post(
            f"/issuance/proposals/{proposal_id}/file-ifsca",
            headers=officer_headers,
            json={"filing_reference": "FIL-001"},
        )
        assert file_response.status_code == 201
        assert file_response.json()["status"] == "IFSCA_FILED"

        ifsca_approve_response = await client.post(
            f"/issuance/proposals/{proposal_id}/ifsca-approve",
            headers=officer_headers,
            json={"approval_reference": "APV-001"},
        )
        assert ifsca_approve_response.status_code == 201
        assert ifsca_approve_response.json()["status"] == "IFSCA_APPROVED"

        # ★ Launch is blocked while disclosures are incomplete.
        premature_launch = await client.post(
            f"/issuance/proposals/{proposal_id}/launch", headers=officer_headers, json={"symbol": "ACME1"}
        )
        assert premature_launch.status_code == 422

        for disclosure_type in DISCLOSURE_TYPES:
            await _upload_disclosure(client, issuer_headers, proposal_id, disclosure_type)

        detail_response = await client.get(f"/issuance/proposals/{proposal_id}", headers=officer_headers)
        assert detail_response.json()["disclosures_complete"] is True

        launch_response = await client.post(
            f"/issuance/proposals/{proposal_id}/launch", headers=officer_headers, json={"symbol": "ACME1"}
        )
        assert launch_response.status_code == 201
        series = launch_response.json()
        assert series["symbol"] == "ACME1"
        assert series["paused"] is False
        series_id = series["id"]

        launched_proposal = await client.get(f"/issuance/proposals/{proposal_id}", headers=officer_headers)
        assert launched_proposal.json()["status"] == "LAUNCHED"

        # Circuit breaker: compliance officer can pause/resume without redeploy.
        pause_response = await client.post(f"/issuance/token-series/{series_id}/pause", headers=officer_headers)
        assert pause_response.status_code == 201
        assert pause_response.json()["paused"] is True

        resume_response = await client.post(f"/issuance/token-series/{series_id}/resume", headers=officer_headers)
        assert resume_response.status_code == 201
        assert resume_response.json()["paused"] is False

    audit_logs = module.get(repository_token(AuditLog))
    actions = [log.action for log in await audit_logs.find()]
    assert "issuance.proposal.created" in actions
    assert "issuance.proposal.submitted_for_review" in actions
    assert "issuance.proposal.compliance_approved" in actions
    assert "issuance.proposal.filed_with_ifsca" in actions
    assert "issuance.proposal.ifsca_approved" in actions
    assert "issuance.proposal.launched" in actions
    assert "issuance.token_series.paused" in actions
    assert "issuance.token_series.resumed" in actions


@pytest.mark.asyncio
async def test_issuer_cannot_review_and_investor_cannot_create_proposals():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        officer_headers = await _login_as(client, module, email="officer2@example.com", role="COMPLIANCE_OFFICER")
        issuer_headers, asset_id = await _create_tokenization_ready_asset(
            client,
            module,
            issuer_email="issuer2@example.com",
            officer_headers=officer_headers,
            registration_no="IFSCA-CUST-E2E-2",
        )
        proposal_id = (
            await client.post("/issuance/proposals", headers=issuer_headers, json=_proposal_body(asset_id))
        ).json()["id"]

        # Issuer cannot approve/review the pipeline.
        assert (
            await client.post(f"/issuance/proposals/{proposal_id}/compliance-approve", headers=issuer_headers)
        ).status_code == 403

        investor_token = await _register_and_login(client, email="investor@example.com")
        investor_headers = {"Authorization": f"Bearer {investor_token}"}
        assert (
            await client.post("/issuance/proposals", headers=investor_headers, json=_proposal_body(asset_id))
        ).status_code == 403


@pytest.mark.asyncio
async def test_create_proposal_rejects_a_non_tokenization_ready_asset_over_http():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        issuer_headers = await _login_as(client, module, email="issuer3@example.com", role="ISSUER")
        await client.post(
            "/issuers/profile",
            headers=issuer_headers,
            json={"legal_name": "No Custody Ltd", "registration_number": "RE-99", "registration_jurisdiction": "in"},
        )
        asset_id = (
            await client.post(
                "/assets", headers=issuer_headers, json={"name": "Bond A", "asset_class": "SECURITY"}
            )
        ).json()["id"]

        response = await client.post("/issuance/proposals", headers=issuer_headers, json=_proposal_body(asset_id))

        assert response.status_code == 409
