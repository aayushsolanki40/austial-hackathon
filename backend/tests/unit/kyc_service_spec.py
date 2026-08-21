"""Unit tests for ``KycService`` -- Phase 2. Exercises the
``DRAFT -> SUBMITTED -> AUTO_SCREENING -> MANUAL_REVIEW -> VERIFIED | REJECTED`` state
machine directly (illegal jumps must raise ``ConflictException``), the mock
OCR/liveness/sanctions pipeline (via Celery's ``task_always_eager``, mirroring
``jobs_spec.py``'s pattern for a hermetic, no-live-Redis test), and the
``AuditLog`` row each transition produces.
"""

from __future__ import annotations

from datetime import date

import pytest
from austial import ConflictException, NotFoundException, UnprocessableEntityException
from austial.orm import DataSource, OrmModule, repository_token
from austial.testing import Test

from src.jobs.celery_app import celery_app
from src.modules.auth.entities.user import User
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.kyc.entities.kyc_document import KycDocument
from src.modules.kyc.entities.kyc_submission import KycSubmission
from src.modules.kyc.entities.risk_disclosure_consent import RiskDisclosureConsent
from src.modules.kyc.kyc_dto import (
    AddKycDocumentDto,
    CreateKycSubmissionDto,
    DocumentUploadUrlRequestDto,
    RecordRiskDisclosureConsentDto,
)
from src.modules.kyc.kyc_service import KycService
from src.storage.object_storage_service import ObjectStorageService


class _FakeObjectStorageService:
    """Stands in for ``ObjectStorageService`` -- no real/moto-backed S3 needed for these
    tests, since ``KycService`` never inspects the URL's contents, only passes it through."""

    def generate_upload_url(self, object_key: str, *, content_type: str, expires_in: int = 900) -> str:
        return f"https://fake-s3.test/{object_key}?content_type={content_type}"

    def generate_download_url(self, object_key: str, *, expires_in: int = 900) -> str:
        return f"https://fake-s3.test/{object_key}"


async def _build_module():
    module = await Test.create_testing_module(
        imports=[
            OrmModule.for_root(
                type_="sqlite",
                url="sqlite+aiosqlite:///:memory:",
                entities=[User, InvestorProfile, KycSubmission, KycDocument, RiskDisclosureConsent, AuditLog],
                synchronize=True,
            ),
            OrmModule.for_feature([User, KycSubmission, KycDocument, RiskDisclosureConsent, InvestorProfile, AuditLog]),
        ],
        providers=[KycService, {"provide": ObjectStorageService, "useValue": _FakeObjectStorageService()}],
    ).compile()
    await module.get(DataSource).initialize()
    return module


async def _seed_investor(module, *, email: str = "investor@example.com") -> InvestorProfile:
    users = module.get(repository_token(User))
    profiles = module.get(repository_token(InvestorProfile))
    user = await users.save(User(email=email, password_hash="hashed", role="INVESTOR"))  # type: ignore[call-arg]
    return await profiles.save(InvestorProfile(user=user, kyc_status="PENDING"))  # type: ignore[call-arg]


_CREATE_DTO = CreateKycSubmissionDto(legal_name="Jane Doe", date_of_birth=date(1990, 1, 1), nationality="in")


@pytest.fixture(autouse=True)
def _task_always_eager():
    # See `jobs_spec.py`'s identical pattern -- runs the mock OCR/liveness/sanctions Celery
    # tasks synchronously in-process, no live Redis broker required.
    celery_app.conf.task_always_eager = True
    try:
        yield
    finally:
        celery_app.conf.task_always_eager = False


@pytest.mark.asyncio
async def test_create_submission_requires_an_investor_profile():
    module = await _build_module()
    service = module.get(KycService)

    with pytest.raises(NotFoundException):
        await service.create_submission(999, _CREATE_DTO)


@pytest.mark.asyncio
async def test_create_submission_starts_in_draft_and_writes_audit_log():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)

    submission = await service.create_submission(profile.user.id, _CREATE_DTO)

    assert submission.status == "DRAFT"
    audit_logs = module.get(repository_token(AuditLog))
    logs = await audit_logs.find()
    assert len(logs) == 1
    assert logs[0].action == "kyc.submission.created"
    assert logs[0].entity_type == "KycSubmission"
    assert logs[0].entity_id == str(submission.id)


@pytest.mark.asyncio
async def test_create_submission_rejects_a_second_active_submission():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)
    await service.create_submission(profile.user.id, _CREATE_DTO)

    with pytest.raises(ConflictException):
        await service.create_submission(profile.user.id, _CREATE_DTO)


@pytest.mark.asyncio
async def test_get_document_upload_url_only_allowed_while_draft():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)
    submission = await service.create_submission(profile.user.id, _CREATE_DTO)

    result = await service.get_document_upload_url(
        profile.user.id, submission.id, DocumentUploadUrlRequestDto(document_type="PASSPORT", content_type="image/png")
    )

    assert result.object_key.startswith(f"kyc/{profile.id}/{submission.id}/passport/")
    assert result.upload_url.startswith("https://fake-s3.test/")


@pytest.mark.asyncio
async def test_submit_rejects_a_submission_with_no_documents():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)
    submission = await service.create_submission(profile.user.id, _CREATE_DTO)

    with pytest.raises(UnprocessableEntityException):
        await service.submit(profile.user.id, submission.id)


async def _submit_with_one_document(module, service: KycService, profile: InvestorProfile):
    submission = await service.create_submission(profile.user.id, _CREATE_DTO)
    await service.add_document(
        profile.user.id, submission.id, AddKycDocumentDto(document_type="PASSPORT", object_key="kyc/x/passport.png")
    )
    await service.record_consent(
        profile.user.id, submission.id, RecordRiskDisclosureConsentDto(disclosure_version="2026-08-21"), None
    )
    return await service.submit(profile.user.id, submission.id)


@pytest.mark.asyncio
async def test_submit_rejects_a_submission_with_documents_but_no_recorded_consent():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)
    submission = await service.create_submission(profile.user.id, _CREATE_DTO)
    await service.add_document(
        profile.user.id, submission.id, AddKycDocumentDto(document_type="PASSPORT", object_key="kyc/x/passport.png")
    )

    with pytest.raises(UnprocessableEntityException):
        await service.submit(profile.user.id, submission.id)


@pytest.mark.asyncio
async def test_record_consent_persists_a_timestamped_consent_row():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)
    submission = await service.create_submission(profile.user.id, _CREATE_DTO)

    consent = await service.record_consent(
        profile.user.id, submission.id, RecordRiskDisclosureConsentDto(disclosure_version="2026-08-21"), "203.0.113.5"
    )

    assert consent.submission_id == submission.id
    assert consent.disclosure_version == "2026-08-21"
    assert consent.acknowledged_at is not None

    consents = module.get(repository_token(RiskDisclosureConsent))
    rows = await consents.find()
    assert len(rows) == 1
    assert rows[0].ip_address == "203.0.113.5"

    submission_dto = await service.get_my_submission(profile.user.id, submission.id)
    assert submission_dto.consent is not None
    assert submission_dto.consent.disclosure_version == "2026-08-21"


@pytest.mark.asyncio
async def test_record_consent_rejects_a_second_consent_for_the_same_submission():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)
    submission = await service.create_submission(profile.user.id, _CREATE_DTO)
    await service.record_consent(
        profile.user.id, submission.id, RecordRiskDisclosureConsentDto(disclosure_version="2026-08-21"), None
    )

    with pytest.raises(ConflictException):
        await service.record_consent(
            profile.user.id, submission.id, RecordRiskDisclosureConsentDto(disclosure_version="2026-08-21"), None
        )


@pytest.mark.asyncio
async def test_record_consent_locked_once_submission_leaves_draft():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)
    submission = await _submit_with_one_document(module, service, profile)

    with pytest.raises(ConflictException):
        await service.record_consent(
            profile.user.id, submission.id, RecordRiskDisclosureConsentDto(disclosure_version="2026-08-21"), None
        )


@pytest.mark.asyncio
async def test_record_consent_requires_own_submission():
    module = await _build_module()
    service = module.get(KycService)
    owner = await _seed_investor(module, email="owner2@example.com")
    other = await _seed_investor(module, email="other2@example.com")
    submission = await service.create_submission(owner.user.id, _CREATE_DTO)

    with pytest.raises(NotFoundException):
        await service.record_consent(
            other.user.id, submission.id, RecordRiskDisclosureConsentDto(disclosure_version="2026-08-21"), None
        )


@pytest.mark.asyncio
async def test_submit_runs_the_full_auto_screening_pipeline_and_lands_in_manual_review():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)

    result = await _submit_with_one_document(module, service, profile)

    assert result.status == "MANUAL_REVIEW"
    assert result.submitted_at is not None
    assert result.screening_result is not None
    assert "liveness" in result.screening_result
    assert "sanctions" in result.screening_result
    assert result.documents[0].ocr_result is not None


@pytest.mark.asyncio
async def test_submit_writes_an_audit_log_row_for_every_transition():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)

    await _submit_with_one_document(module, service, profile)

    audit_logs = module.get(repository_token(AuditLog))
    actions = [log.action for log in await audit_logs.find()]
    assert "kyc.submission.created" in actions
    assert "kyc.submission.consent_recorded" in actions
    assert "kyc.submission.submitted" in actions
    assert "kyc.submission.auto_screening_started" in actions
    assert "kyc.submission.entered_manual_review" in actions


@pytest.mark.asyncio
async def test_documents_locked_once_submission_leaves_draft():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)
    submission = await _submit_with_one_document(module, service, profile)

    with pytest.raises(ConflictException):
        await service.add_document(
            profile.user.id, submission.id, AddKycDocumentDto(document_type="SELFIE", object_key="kyc/x/selfie.png")
        )


@pytest.mark.asyncio
async def test_approve_requires_manual_review_status():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)
    submission = await service.create_submission(profile.user.id, _CREATE_DTO)

    with pytest.raises(ConflictException):
        await service.approve(officer_id=1, submission_id=submission.id)


@pytest.mark.asyncio
async def test_approve_transitions_to_verified_and_flips_investor_kyc_status():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)
    submission = await _submit_with_one_document(module, service, profile)

    approved = await service.approve(officer_id=42, submission_id=submission.id)

    assert approved.status == "VERIFIED"
    investor_profiles = module.get(repository_token(InvestorProfile))
    reloaded = await investor_profiles.find_one_by({"id": profile.id})
    assert reloaded.kyc_status == "VERIFIED"

    audit_logs = module.get(repository_token(AuditLog))
    actions = [log.action for log in await audit_logs.find()]
    assert "kyc.submission.approved" in actions


@pytest.mark.asyncio
async def test_reject_transitions_to_rejected_with_reason_and_flips_investor_kyc_status():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)
    submission = await _submit_with_one_document(module, service, profile)

    rejected = await service.reject(officer_id=42, submission_id=submission.id, reason="Blurry document")

    assert rejected.status == "REJECTED"
    assert rejected.review_notes == "Blurry document"
    investor_profiles = module.get(repository_token(InvestorProfile))
    reloaded = await investor_profiles.find_one_by({"id": profile.id})
    assert reloaded.kyc_status == "REJECTED"


@pytest.mark.asyncio
async def test_verified_and_rejected_are_terminal_states():
    module = await _build_module()
    service = module.get(KycService)
    profile = await _seed_investor(module)
    submission = await _submit_with_one_document(module, service, profile)
    await service.approve(officer_id=1, submission_id=submission.id)

    with pytest.raises(ConflictException):
        await service.approve(officer_id=1, submission_id=submission.id)
    with pytest.raises(ConflictException):
        await service.reject(officer_id=1, submission_id=submission.id, reason="too late")


@pytest.mark.asyncio
async def test_list_pending_review_only_returns_manual_review_submissions():
    module = await _build_module()
    service = module.get(KycService)
    profile_pending = await _seed_investor(module, email="pending@example.com")
    profile_draft = await _seed_investor(module, email="draft@example.com")
    await _submit_with_one_document(module, service, profile_pending)
    await service.create_submission(profile_draft.user.id, _CREATE_DTO)

    page = await service.list_pending_review(skip=0, take=50)

    assert page.total == 1
    assert page.items[0].status == "MANUAL_REVIEW"


@pytest.mark.asyncio
async def test_get_my_submission_rejects_access_to_another_investors_submission():
    module = await _build_module()
    service = module.get(KycService)
    owner = await _seed_investor(module, email="owner@example.com")
    other = await _seed_investor(module, email="other@example.com")
    submission = await service.create_submission(owner.user.id, _CREATE_DTO)

    with pytest.raises(NotFoundException):
        await service.get_my_submission(other.user.id, submission.id)
