"""End-to-end tests for the Phase 2 KYC flow -- proves the exit criteria from the build
plan: register -> create investor profile -> submit KYC -> (mock) auto-screening ->
manual-review approval -> ``VERIFIED``, with ``AuditLog`` rows for every transition.
Mirrors ``admin_e2e_spec.py``'s pattern (real ``/auth`` flow + direct-repository role
promotion, since there's no public self-promotion route to ``COMPLIANCE_OFFICER``).
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
from src.jobs.celery_app import celery_app
from src.modules.auth.auth_module import AuthModule
from src.modules.auth.entities.refresh_token import RefreshToken
from src.modules.auth.entities.user import User
from src.modules.compliance.compliance_module import ComplianceModule
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.compliance.interceptors.audit_interceptor import AuditInterceptor
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.investors.entities.wallet_mapping import WalletMapping
from src.modules.investors.investors_module import InvestorsModule
from src.modules.kyc.entities.kyc_document import KycDocument
from src.modules.kyc.entities.kyc_submission import KycSubmission
from src.modules.kyc.entities.risk_disclosure_consent import RiskDisclosureConsent
from src.modules.kyc.kyc_module import KycModule

_BUCKET = "austial-documents-kyc-e2e-test"
_REGION = "us-east-1"


def _config_service() -> ConfigService:
    return ConfigService({"JWT_SECRET": "kyc-e2e-test-secret", "DOCUMENTS_S3_BUCKET": _BUCKET, "AWS_REGION": _REGION})


@pytest.fixture(autouse=True)
def _hermetic_infra():
    # No live Redis broker (`task_always_eager`, mirrors `jobs_spec.py`) and no live AWS
    # (`moto`'s `mock_aws`, mirrors `object_storage_service_spec.py`) -- `KycService.submit()`
    # touches both (Celery tasks for the mock auto-screening pipeline, S3 presigned URLs for
    # document upload).
    celery_app.conf.task_always_eager = True
    with mock_aws():
        client = boto3.client("s3", region_name=_REGION)
        client.create_bucket(Bucket=_BUCKET)
        try:
            yield
        finally:
            celery_app.conf.task_always_eager = False


async def _build_app_and_module():
    orm_module = OrmModule.for_root(
        type_="sqlite",
        url="sqlite+aiosqlite:///:memory:",
        entities=[
            User,
            RefreshToken,
            InvestorProfile,
            WalletMapping,
            KycSubmission,
            KycDocument,
            RiskDisclosureConsent,
            AuditLog,
        ],
        synchronize=True,
    )
    module = await Test.create_testing_module(
        imports=[orm_module, AuthModule, InvestorsModule, KycModule, ComplianceModule],
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


async def _promote_to_compliance_officer(module, *, email: str) -> None:
    users = module.get(repository_token(User))
    user = await users.find_one_by({"email": email})
    user.role = "COMPLIANCE_OFFICER"
    await users.save(user)


@pytest.mark.asyncio
async def test_full_kyc_flow_reaches_verified_with_audit_trail():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        investor_token = await _register_and_login(client, email="investor@example.com")
        investor_headers = {"Authorization": f"Bearer {investor_token}"}

        profile_response = await client.post(
            "/investors/profile",
            headers=investor_headers,
            json={"investor_type": "INDIVIDUAL", "jurisdiction": "in", "risk_profile": "MODERATE"},
        )
        assert profile_response.status_code == 201
        assert profile_response.json()["kyc_status"] == "PENDING"

        submission_response = await client.post(
            "/kyc/submissions",
            headers=investor_headers,
            json={"legal_name": "Jane Doe", "date_of_birth": "1990-01-01", "nationality": "in"},
        )
        assert submission_response.status_code == 201
        submission = submission_response.json()
        assert submission["status"] == "DRAFT"
        submission_id = submission["id"]

        upload_url_response = await client.post(
            f"/kyc/submissions/{submission_id}/documents/upload-url",
            headers=investor_headers,
            json={"document_type": "PASSPORT", "content_type": "image/png"},
        )
        assert upload_url_response.status_code == 201
        object_key = upload_url_response.json()["object_key"]

        add_document_response = await client.post(
            f"/kyc/submissions/{submission_id}/documents",
            headers=investor_headers,
            json={"document_type": "PASSPORT", "object_key": object_key},
        )
        assert add_document_response.status_code == 201

        consent_response = await client.post(
            f"/kyc/submissions/{submission_id}/consent",
            headers=investor_headers,
            json={"disclosure_version": "2026-08-21"},
        )
        assert consent_response.status_code == 201
        consent_body = consent_response.json()
        assert consent_body["submission_id"] == submission_id
        assert consent_body["disclosure_version"] == "2026-08-21"
        assert consent_body["acknowledged_at"] is not None

        get_submission_response = await client.get(f"/kyc/submissions/{submission_id}", headers=investor_headers)
        assert get_submission_response.json()["consent"]["disclosure_version"] == "2026-08-21"

        submit_response = await client.post(f"/kyc/submissions/{submission_id}/submit", headers=investor_headers)
        assert submit_response.status_code == 201
        submitted = submit_response.json()
        assert submitted["status"] == "MANUAL_REVIEW"
        assert submitted["screening_result"] is not None
        assert submitted["consent"]["disclosure_version"] == "2026-08-21"

        # A compliance officer (not the investor) reviews and approves.
        await _register_and_login(client, email="officer@example.com")
        await _promote_to_compliance_officer(module, email="officer@example.com")
        officer_token = await _register_and_login(client, email="officer@example.com")
        officer_headers = {"Authorization": f"Bearer {officer_token}"}

        queue_response = await client.get("/kyc/review-queue", headers=officer_headers)
        assert queue_response.status_code == 200
        queue_body = queue_response.json()
        assert queue_body["total"] == 1
        assert queue_body["items"][0]["id"] == submission_id

        approve_response = await client.post(f"/kyc/submissions/{submission_id}/approve", headers=officer_headers)
        assert approve_response.status_code == 201
        assert approve_response.json()["status"] == "VERIFIED"

        # The investor's own profile now reflects the VERIFIED status.
        my_profile_response = await client.get("/investors/profile", headers=investor_headers)
        assert my_profile_response.json()["kyc_status"] == "VERIFIED"

    audit_logs = module.get(repository_token(AuditLog))
    actions = [log.action for log in await audit_logs.find()]
    assert "kyc.submission.created" in actions
    assert "kyc.submission.consent_recorded" in actions
    assert "kyc.submission.submitted" in actions
    assert "kyc.submission.auto_screening_started" in actions
    assert "kyc.submission.entered_manual_review" in actions
    assert "kyc.submission.approved" in actions


@pytest.mark.asyncio
async def test_compliance_officer_can_reject_with_a_reason():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        investor_token = await _register_and_login(client, email="reject-me@example.com")
        investor_headers = {"Authorization": f"Bearer {investor_token}"}
        await client.post(
            "/investors/profile",
            headers=investor_headers,
            json={"investor_type": "INDIVIDUAL", "jurisdiction": "IN", "risk_profile": "MODERATE"},
        )
        submission_id = (
            await client.post(
                "/kyc/submissions",
                headers=investor_headers,
                json={"legal_name": "John Reject", "date_of_birth": "1985-05-05", "nationality": "US"},
            )
        ).json()["id"]
        await client.post(
            f"/kyc/submissions/{submission_id}/documents",
            headers=investor_headers,
            json={"document_type": "NATIONAL_ID", "object_key": "kyc/manual/national-id.png"},
        )
        await client.post(
            f"/kyc/submissions/{submission_id}/consent",
            headers=investor_headers,
            json={"disclosure_version": "2026-08-21"},
        )
        await client.post(f"/kyc/submissions/{submission_id}/submit", headers=investor_headers)

        await _register_and_login(client, email="officer2@example.com")
        await _promote_to_compliance_officer(module, email="officer2@example.com")
        officer_token = await _register_and_login(client, email="officer2@example.com")
        officer_headers = {"Authorization": f"Bearer {officer_token}"}

        reject_response = await client.post(
            f"/kyc/submissions/{submission_id}/reject",
            headers=officer_headers,
            json={"reason": "Document image is blurry"},
        )

        assert reject_response.status_code == 201
        body = reject_response.json()
        assert body["status"] == "REJECTED"
        assert body["review_notes"] == "Document image is blurry"

    audit_logs = module.get(repository_token(AuditLog))
    actions = [log.action for log in await audit_logs.find()]
    assert "kyc.submission.rejected" in actions


@pytest.mark.asyncio
async def test_investor_cannot_access_the_review_queue_and_officer_cannot_submit_kyc():
    app, module = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        investor_token = await _register_and_login(client, email="plain-investor@example.com")
        investor_headers = {"Authorization": f"Bearer {investor_token}"}

        assert (await client.get("/kyc/review-queue", headers=investor_headers)).status_code == 403

        await _register_and_login(client, email="officer3@example.com")
        await _promote_to_compliance_officer(module, email="officer3@example.com")
        officer_token = await _register_and_login(client, email="officer3@example.com")
        officer_headers = {"Authorization": f"Bearer {officer_token}"}

        create_response = await client.post(
            "/kyc/submissions",
            headers=officer_headers,
            json={"legal_name": "Officer Trying", "date_of_birth": "1980-01-01", "nationality": "IN"},
        )
        assert create_response.status_code == 403


@pytest.mark.asyncio
async def test_submitting_without_documents_is_rejected():
    app, _ = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        token = await _register_and_login(client, email="no-docs@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        await client.post(
            "/investors/profile",
            headers=headers,
            json={"investor_type": "INDIVIDUAL", "jurisdiction": "IN", "risk_profile": "CONSERVATIVE"},
        )
        submission_id = (
            await client.post(
                "/kyc/submissions",
                headers=headers,
                json={"legal_name": "No Docs", "date_of_birth": "1990-01-01", "nationality": "IN"},
            )
        ).json()["id"]

        response = await client.post(f"/kyc/submissions/{submission_id}/submit", headers=headers)

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_submitting_without_recorded_consent_is_rejected():
    app, _ = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        token = await _register_and_login(client, email="no-consent@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        await client.post(
            "/investors/profile",
            headers=headers,
            json={"investor_type": "INDIVIDUAL", "jurisdiction": "IN", "risk_profile": "CONSERVATIVE"},
        )
        submission_id = (
            await client.post(
                "/kyc/submissions",
                headers=headers,
                json={"legal_name": "No Consent", "date_of_birth": "1990-01-01", "nationality": "IN"},
            )
        ).json()["id"]
        await client.post(
            f"/kyc/submissions/{submission_id}/documents",
            headers=headers,
            json={"document_type": "PASSPORT", "object_key": "kyc/manual/passport.png"},
        )

        response = await client.post(f"/kyc/submissions/{submission_id}/submit", headers=headers)

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_consent_cannot_be_recorded_twice_for_the_same_submission():
    app, _ = await _build_app_and_module()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        token = await _register_and_login(client, email="double-consent@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        await client.post(
            "/investors/profile",
            headers=headers,
            json={"investor_type": "INDIVIDUAL", "jurisdiction": "IN", "risk_profile": "CONSERVATIVE"},
        )
        submission_id = (
            await client.post(
                "/kyc/submissions",
                headers=headers,
                json={"legal_name": "Double Consent", "date_of_birth": "1990-01-01", "nationality": "IN"},
            )
        ).json()["id"]

        first = await client.post(
            f"/kyc/submissions/{submission_id}/consent",
            headers=headers,
            json={"disclosure_version": "2026-08-21"},
        )
        assert first.status_code == 201

        second = await client.post(
            f"/kyc/submissions/{submission_id}/consent",
            headers=headers,
            json={"disclosure_version": "2026-08-21"},
        )
        assert second.status_code == 409
