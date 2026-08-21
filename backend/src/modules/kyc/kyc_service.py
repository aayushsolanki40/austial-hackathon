"""``KycService`` -- Phase 2. Owns the ``KycSubmission`` state machine::

    DRAFT -> SUBMITTED -> AUTO_SCREENING -> MANUAL_REVIEW -> VERIFIED | REJECTED

Every transition is (a) checked against ``ALLOWED_TRANSITIONS`` -- an illegal jump raises
``ConflictException`` rather than silently applying -- and (b) written to ``AuditLog`` directly
(in addition to, not instead of, the generic global ``AuditInterceptor`` every mutating HTTP
request already produces -- see that class's docstring), mirroring ``AdminService``'s existing
convention for regulator-sensitive before/after diffs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from austial import ConflictException, Injectable, NotFoundException, UnprocessableEntityException
from austial.orm import FindOptions, InjectRepository, Repository

from src.i18n.i18n import t
from src.jobs.kyc_tasks import (
    run_liveness_face_match_task,
    run_ocr_extraction_task,
    run_sanctions_screening_task,
)
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.kyc.entities.kyc_document import KycDocument
from src.modules.kyc.entities.kyc_submission import KycSubmission
from src.modules.kyc.entities.risk_disclosure_consent import RiskDisclosureConsent
from src.modules.kyc.kyc_dto import (
    AddKycDocumentDto,
    CreateKycSubmissionDto,
    DocumentUploadUrlRequestDto,
    DocumentUploadUrlResponseDto,
    KycDocumentResponseDto,
    KycSubmissionListDto,
    KycSubmissionResponseDto,
    RecordRiskDisclosureConsentDto,
    RiskDisclosureConsentResponseDto,
)
from src.storage.object_storage_service import ObjectStorageService

# Legal status transitions -- anything not listed here (including no-op "transitions" to the
# current status) is rejected by `_assert_transition`.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SUBMITTED"},
    "SUBMITTED": {"AUTO_SCREENING"},
    "AUTO_SCREENING": {"MANUAL_REVIEW"},
    "MANUAL_REVIEW": {"VERIFIED", "REJECTED"},
    "VERIFIED": set(),
    "REJECTED": set(),
}

# Generous relative to how fast the mock providers actually return (near-instant) -- see
# `src/jobs/kyc_tasks.py`'s module docstring for why blocking `.get()` here is a Phase-2-only,
# mock-provider-only pattern that must not be copied forward for a real (potentially slow)
# Phase 9 OCR/liveness/sanctions integration.
_MOCK_TASK_RESULT_TIMEOUT_SECONDS = 10


@Injectable()
class KycService:
    def __init__(
        self,
        storage: ObjectStorageService,
        submissions: Repository[KycSubmission] = InjectRepository(KycSubmission),
        documents: Repository[KycDocument] = InjectRepository(KycDocument),
        investor_profiles: Repository[InvestorProfile] = InjectRepository(InvestorProfile),
        audit_logs: Repository[AuditLog] = InjectRepository(AuditLog),
        consents: Repository[RiskDisclosureConsent] = InjectRepository(RiskDisclosureConsent),
    ):
        self.submissions = submissions
        self.documents = documents
        self.investor_profiles = investor_profiles
        self.audit_logs = audit_logs
        self.consents = consents
        self.storage = storage

    # -- investor-facing API -----------------------------------------------------------------

    async def create_submission(self, user_id: int, dto: CreateKycSubmissionDto) -> KycSubmissionResponseDto:
        profile = await self._get_investor_profile_or_raise(user_id)
        if await self._has_active_submission(profile.id):
            raise ConflictException(t("kyc.error.active_submission_exists"))

        submission = await self.submissions.save(
            # `# type: ignore[call-arg]` -- see the note on `User(...)` in `AuthService.register()`
            # (`austial-py` `py.typed` gap, tracked for `austial-framework-dev`).
            KycSubmission(  # type: ignore[call-arg]
                investor=profile,
                status="DRAFT",
                legal_name=dto.legal_name,
                date_of_birth=dto.date_of_birth,
                nationality=dto.nationality,
            )
        )
        await self._write_audit_log(
            submission_id=submission.id,
            actor_user_id=user_id,
            action="kyc.submission.created",
            before_state=None,
            after_state={"status": "DRAFT"},
        )
        return self._to_submission_dto(submission, investor_id=profile.id, documents=[], consent=None)

    async def get_document_upload_url(
        self, user_id: int, submission_id: int, dto: DocumentUploadUrlRequestDto
    ) -> DocumentUploadUrlResponseDto:
        submission = await self._get_own_submission_or_raise(submission_id, user_id)
        if submission.status != "DRAFT":
            raise ConflictException(t("kyc.error.documents_locked"))

        object_key = f"kyc/{submission.investor.id}/{submission.id}/{dto.document_type.lower()}/{uuid.uuid4().hex}"
        upload_url = self.storage.generate_upload_url(object_key, content_type=dto.content_type)
        return DocumentUploadUrlResponseDto(upload_url=upload_url, object_key=object_key)

    async def add_document(self, user_id: int, submission_id: int, dto: AddKycDocumentDto) -> KycDocumentResponseDto:
        submission = await self._get_own_submission_or_raise(submission_id, user_id)
        if submission.status != "DRAFT":
            raise ConflictException(t("kyc.error.documents_locked"))

        document = await self.documents.save(
            KycDocument(submission=submission, document_type=dto.document_type, object_key=dto.object_key)  # type: ignore[call-arg]
        )
        return _to_document_dto(document)

    async def record_consent(
        self, user_id: int, submission_id: int, dto: RecordRiskDisclosureConsentDto, ip_address: str | None
    ) -> RiskDisclosureConsentResponseDto:
        """Persists the investor's risk-disclosure acknowledgment -- see
        ``RiskDisclosureConsent``'s docstring for why this must be a real DB row, not a
        client-side flag. One consent row per submission (mirrors ``documents_locked``):
        recording it again for an already-consented submission is rejected outright rather than
        silently overwritten, since a create-once record has no legitimate "update" case.
        """
        submission = await self._get_own_submission_or_raise(submission_id, user_id)
        if submission.status != "DRAFT":
            raise ConflictException(t("kyc.error.consent_locked"))
        if await self._get_consent(submission.id) is not None:
            raise ConflictException(t("kyc.error.consent_already_recorded"))

        consent = await self.consents.save(
            RiskDisclosureConsent(  # type: ignore[call-arg]
                submission=submission,
                disclosure_version=dto.disclosure_version,
                ip_address=ip_address,
            )
        )
        await self._write_audit_log(
            submission_id=submission.id,
            actor_user_id=user_id,
            action="kyc.submission.consent_recorded",
            before_state=None,
            after_state={"disclosure_version": dto.disclosure_version},
        )
        return _to_consent_dto(consent, submission_id=submission.id)

    async def get_my_submission(self, user_id: int, submission_id: int) -> KycSubmissionResponseDto:
        submission = await self._get_own_submission_or_raise(submission_id, user_id)
        documents = await self._list_documents(submission.id)
        consent = await self._get_consent(submission.id)
        return self._to_submission_dto(
            submission, investor_id=submission.investor.id, documents=documents, consent=consent
        )

    async def list_my_submissions(self, user_id: int) -> list[KycSubmissionResponseDto]:
        profile = await self._get_investor_profile_or_raise(user_id)
        submissions = await (
            self.submissions.create_query_builder("s")
            .where("s.investor_id = :investor_id", {"investor_id": profile.id})
            .add_order_by("s.id", "DESC")
            .get_many()
        )
        result = []
        for submission in submissions:
            documents = await self._list_documents(submission.id)
            consent = await self._get_consent(submission.id)
            result.append(
                self._to_submission_dto(submission, investor_id=profile.id, documents=documents, consent=consent)
            )
        return result

    async def submit(self, user_id: int, submission_id: int) -> KycSubmissionResponseDto:
        """``DRAFT -> SUBMITTED -> AUTO_SCREENING`` (both system-driven, no external actor to
        gate on), runs the mock auto-screening pipeline synchronously, then
        ``AUTO_SCREENING -> MANUAL_REVIEW``. See ``_run_auto_screening_pipeline``'s docstring for
        why the synchronous/blocking pipeline call is a mock-provider-only pattern.

        ★ Gated on a recorded ``RiskDisclosureConsent`` for this submission, in addition to the
        pre-existing "at least one document" gate -- see ``AUSTIAL_BUILD_PLAN.md`` Section 3's
        login-flow note: disclosure acknowledgment is a required step, not optional, so a
        submission cannot leave ``DRAFT`` without one on file.
        """
        submission = await self._get_own_submission_or_raise(submission_id, user_id)
        self._assert_transition(submission.status, "SUBMITTED")

        documents = await self._list_documents(submission.id)
        if not documents:
            raise UnprocessableEntityException(t("kyc.error.no_documents"))

        if await self._get_consent(submission.id) is None:
            raise UnprocessableEntityException(t("kyc.error.consent_required"))

        await self._transition(submission, "SUBMITTED", actor_user_id=user_id, action="kyc.submission.submitted")
        submission.submitted_at = datetime.now(UTC).replace(tzinfo=None)
        await self.submissions.save(submission)

        await self._transition(
            submission, "AUTO_SCREENING", actor_user_id=user_id, action="kyc.submission.auto_screening_started"
        )

        submission.screening_result = await self._run_auto_screening_pipeline(submission, documents)
        await self.submissions.save(submission)

        await self._transition(
            submission,
            "MANUAL_REVIEW",
            actor_user_id=user_id,
            action="kyc.submission.entered_manual_review",
            extra_after={"screening_result": submission.screening_result},
        )

        consent = await self._get_consent(submission.id)
        return self._to_submission_dto(
            submission, investor_id=submission.investor.id, documents=documents, consent=consent
        )

    # -- compliance-officer-facing API (review queue) ----------------------------------------

    async def list_pending_review(self, *, skip: int, take: int) -> KycSubmissionListDto:
        submissions, total = await (
            self.submissions.create_query_builder("s")
            .where("CAST(s.status AS TEXT) = :status", {"status": "MANUAL_REVIEW"})
            .left_join_and_select("s.investor", "investor")
            .add_order_by("s.id", "ASC")
            .skip(skip)
            .take(take)
            .get_many_and_count()
        )
        items = []
        for submission in submissions:
            documents = await self._list_documents(submission.id)
            consent = await self._get_consent(submission.id)
            items.append(
                self._to_submission_dto(
                    submission, investor_id=submission.investor.id, documents=documents, consent=consent
                )
            )
        return KycSubmissionListDto(total=total, items=items)

    async def approve(self, officer_id: int, submission_id: int) -> KycSubmissionResponseDto:
        submission = await self._get_submission_with_investor_or_raise(submission_id)
        self._assert_transition(submission.status, "VERIFIED")

        submission.reviewed_by_user_id = officer_id
        await self._transition(submission, "VERIFIED", actor_user_id=officer_id, action="kyc.submission.approved")
        await self._flip_investor_kyc_status(submission.investor, "VERIFIED")

        documents = await self._list_documents(submission.id)
        consent = await self._get_consent(submission.id)
        return self._to_submission_dto(
            submission, investor_id=submission.investor.id, documents=documents, consent=consent
        )

    async def reject(self, officer_id: int, submission_id: int, reason: str) -> KycSubmissionResponseDto:
        submission = await self._get_submission_with_investor_or_raise(submission_id)
        self._assert_transition(submission.status, "REJECTED")

        submission.reviewed_by_user_id = officer_id
        submission.review_notes = reason
        await self._transition(
            submission,
            "REJECTED",
            actor_user_id=officer_id,
            action="kyc.submission.rejected",
            extra_after={"review_notes": reason},
        )
        await self._flip_investor_kyc_status(submission.investor, "REJECTED")

        documents = await self._list_documents(submission.id)
        consent = await self._get_consent(submission.id)
        return self._to_submission_dto(
            submission, investor_id=submission.investor.id, documents=documents, consent=consent
        )

    # -- internals ----------------------------------------------------------------------------

    def _assert_transition(self, current_status: str, target_status: str) -> None:
        if target_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
            raise ConflictException(
                t("kyc.error.invalid_transition").format(current=current_status, target=target_status)
            )

    async def _transition(
        self,
        submission: KycSubmission,
        target_status: str,
        *,
        actor_user_id: int,
        action: str,
        extra_after: dict[str, Any] | None = None,
    ) -> None:
        before_status = submission.status
        submission.status = target_status
        await self.submissions.save(submission)
        await self._write_audit_log(
            submission_id=submission.id,
            actor_user_id=actor_user_id,
            action=action,
            before_state={"status": before_status},
            after_state={"status": target_status, **(extra_after or {})},
        )

    async def _run_auto_screening_pipeline(
        self, submission: KycSubmission, documents: list[KycDocument]
    ) -> dict[str, Any]:
        """Runs OCR (per document), liveness/face-match, and sanctions screening via the
        Celery tasks in ``src/jobs/kyc_tasks.py`` (each a thin wrapper over a swappable
        ``mock`` provider -- see that module's docstring).

        ★ Blocks on ``.get()`` for each task's result. This is only acceptable because every
        provider involved today is a mock that returns near-instantly and does no real I/O.
        A real Phase 9 OCR/liveness/sanctions integration (seconds of latency, real external
        API calls) MUST NOT be orchestrated this way -- that needs a true async callback/
        polling design, not a blocking call inside an HTTP request handler. Flagged here
        deliberately so swapping the *provider* alone doesn't silently carry this forward.
        """
        for document in documents:
            result = run_ocr_extraction_task.delay(
                document_type=document.document_type, object_key=document.object_key
            ).get(timeout=_MOCK_TASK_RESULT_TIMEOUT_SECONDS)
            document.ocr_result = result
            # `Repository.update(criteria, partial)` (a targeted `UPDATE ... SET ocr_result = ...`),
            # not `.save(document)` -- `document` here comes from `_list_documents()`'s raw
            # query-builder select, which never eager-loads `document.submission` (relations are
            # lazy unless explicitly requested -- see `EntityManager.save()`'s own docstring).
            # `.save()` always does a full-column UPDATE, and would compute the owning
            # `submission_id` FK from the (unloaded, `None`) `document.submission` attribute,
            # silently overwriting it with `NULL` -- `.update()` only ever touches the columns
            # named in `partial`, so it can't clobber a relation it never looked at.
            await self.documents.update({"id": document.id}, {"ocr_result": result})

        selfie = next((d for d in documents if d.document_type == "SELFIE"), None)
        id_document = next((d for d in documents if d.document_type != "SELFIE"), documents[0])

        liveness_result = run_liveness_face_match_task.delay(
            submission_id=submission.id,
            selfie_object_key=selfie.object_key if selfie else "",
            id_document_object_key=id_document.object_key,
        ).get(timeout=_MOCK_TASK_RESULT_TIMEOUT_SECONDS)

        sanctions_result = run_sanctions_screening_task.delay(
            legal_name=submission.legal_name, nationality=submission.nationality
        ).get(timeout=_MOCK_TASK_RESULT_TIMEOUT_SECONDS)

        return {"liveness": liveness_result, "sanctions": sanctions_result}

    async def _has_active_submission(self, investor_id: int) -> bool:
        existing = await (
            self.submissions.create_query_builder("s")
            .where("s.investor_id = :investor_id", {"investor_id": investor_id})
            .and_where(
                "CAST(s.status AS TEXT) NOT IN (:verified, :rejected)",
                {"verified": "VERIFIED", "rejected": "REJECTED"},
            )
            .get_one()
        )
        return existing is not None

    async def _list_documents(self, submission_id: int) -> list[KycDocument]:
        return await (
            self.documents.create_query_builder("d")
            .where("d.submission_id = :submission_id", {"submission_id": submission_id})
            .add_order_by("d.id", "ASC")
            .get_many()
        )

    async def _get_consent(self, submission_id: int) -> RiskDisclosureConsent | None:
        return await (
            self.consents.create_query_builder("c")
            .where("c.submission_id = :submission_id", {"submission_id": submission_id})
            .get_one()
        )

    async def _get_investor_profile_or_raise(self, user_id: int) -> InvestorProfile:
        profile = await (
            self.investor_profiles.create_query_builder("investor_profile")
            .where("investor_profile.user_id = :user_id", {"user_id": user_id})
            .get_one()
        )
        if profile is None:
            raise NotFoundException(t("kyc.error.investor_profile_required"))
        return profile

    async def _get_own_submission_or_raise(self, submission_id: int, user_id: int) -> KycSubmission:
        profile = await self._get_investor_profile_or_raise(user_id)
        submission = await self.submissions.find_one(FindOptions(where={"id": submission_id}, relations=["investor"]))
        if submission is None or submission.investor is None or submission.investor.id != profile.id:
            raise NotFoundException(t("kyc.error.submission_not_found"))
        return submission

    async def _get_submission_with_investor_or_raise(self, submission_id: int) -> KycSubmission:
        submission = await self.submissions.find_one(FindOptions(where={"id": submission_id}, relations=["investor"]))
        if submission is None:
            raise NotFoundException(t("kyc.error.submission_not_found"))
        return submission

    async def _flip_investor_kyc_status(self, profile: InvestorProfile, kyc_status: str) -> None:
        # `.update(...)`, not `.save(profile)`, for the same reason as the `ocr_result` update
        # above -- `profile` here is `submission.investor`, hydrated by the *outer* query's
        # `relations=["investor"]`/`.left_join_and_select("s.investor", ...)`, which does not
        # transitively eager-load `investor.user` too. A full-column `.save(profile)` would read
        # that unloaded `profile.user` (`None`) and null out `investor_profile.user_id` -- silently
        # unlinking the profile from its account, since that FK is nullable (no `IntegrityError`
        # to catch the mistake). `.update()` only ever touches `kyc_status`.
        profile.kyc_status = kyc_status
        await self.investor_profiles.update({"id": profile.id}, {"kyc_status": kyc_status})

    async def _write_audit_log(
        self,
        *,
        submission_id: int,
        actor_user_id: int | None,
        action: str,
        before_state: dict[str, Any] | None,
        after_state: dict[str, Any] | None,
    ) -> None:
        # In addition to (not instead of) the generic `AuditInterceptor` row every mutating
        # request already produces -- see that class's docstring, and `AdminService`'s
        # `_write_audit_log` for the identical convention this mirrors.
        await self.audit_logs.save(
            AuditLog(  # type: ignore[call-arg]
                actor_user_id=actor_user_id,
                action=action,
                entity_type="KycSubmission",
                entity_id=str(submission_id),
                before_state=before_state,
                after_state=after_state,
                ip_address=None,
            )
        )

    def _to_submission_dto(
        self,
        submission: KycSubmission,
        *,
        investor_id: int,
        documents: list[KycDocument],
        consent: RiskDisclosureConsent | None,
    ) -> KycSubmissionResponseDto:
        return KycSubmissionResponseDto(
            id=submission.id,
            investor_id=investor_id,
            status=submission.status,
            legal_name=submission.legal_name,
            date_of_birth=submission.date_of_birth,
            nationality=submission.nationality,
            submitted_at=submission.submitted_at,
            screening_result=submission.screening_result,
            reviewed_by_user_id=submission.reviewed_by_user_id,
            review_notes=submission.review_notes,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
            documents=[_to_document_dto(doc) for doc in documents],
            consent=_to_consent_dto(consent, submission_id=submission.id) if consent is not None else None,
        )


def _to_document_dto(document: KycDocument) -> KycDocumentResponseDto:
    return KycDocumentResponseDto(
        id=document.id,
        document_type=document.document_type,
        object_key=document.object_key,
        ocr_result=document.ocr_result,
        created_at=document.created_at,
    )


def _to_consent_dto(consent: RiskDisclosureConsent, *, submission_id: int) -> RiskDisclosureConsentResponseDto:
    # `submission_id` is passed in explicitly by the caller rather than read off
    # `consent.submission.id` -- `consent` here may come from `_get_consent()`'s raw
    # query-builder select, which never eager-loads `consent.submission` (relations are lazy
    # unless explicitly requested), and every call site already has the submission's id in
    # scope. Mirrors the same lazy-relation caution documented on `_run_auto_screening_pipeline`'s
    # `Repository.update(...)` call and `_flip_investor_kyc_status`.
    return RiskDisclosureConsentResponseDto(
        id=consent.id,
        submission_id=submission_id,
        disclosure_version=consent.disclosure_version,
        acknowledged_at=consent.acknowledged_at,
    )
