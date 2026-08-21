"""KYC pipeline Celery tasks -- Phase 2.

Three tasks per ``AUSTIAL_BUILD_PLAN.md``'s Phase 2 scope (OCR extraction, liveness/face-match,
sanctions screening) plus a periodic re-screening task *shape*. Each task is a thin, stateless
wrapper around one of the swappable provider interfaces in ``src/modules/kyc/providers/`` --
today every task instantiates that provider's ``Mock...`` implementation; Phase 9 swaps the
concrete provider class constructed here for a real one, and nothing else in this file (or in
``KycService``'s orchestration) needs to change.

**Deliberately no DB access inside a task.** These run in a separate Celery worker process, not
inside the app's async DI graph, and this app's ``DataSource`` is async (asyncpg) -- mixing a sync
Celery worker with the async ORM would need its own event loop / connection-pool plumbing this
phase doesn't need yet, since the mock providers are pure, instantaneous, side-effect-free
functions. Each task takes primitive JSON-serializable input and returns a JSON-serializable
result dict; ``KycService`` (the caller, which *does* have DB access) persists whatever it needs
from that result onto the relevant entity.

**Synchronous ``.delay().get()`` orchestration note** (see ``kyc_service.py``'s
``_run_auto_screening_pipeline`` docstring for the full rationale): ``KycService`` blocks on task
results today because these mock providers return near-instantly. A real Phase 9 OCR/liveness/
sanctions integration will likely take seconds and **must not** be orchestrated this way --
that's a true async job (webhook callback or polling), not a blocking ``.get()`` inside an HTTP
request handler. Flagged here so Phase 9 doesn't just swap the provider and keep the blocking
call.
"""

from __future__ import annotations

from typing import Any

from src.jobs.celery_app import celery_app
from src.modules.kyc.providers.liveness_provider import MockLivenessProvider
from src.modules.kyc.providers.ocr_provider import MockOcrProvider
from src.modules.kyc.providers.sanctions_screening_provider import MockSanctionsScreeningProvider

# Module-level singletons -- Celery tasks are plain functions with no DI container of their own
# (see this module's docstring), so the provider instances live here rather than being
# constructor-injected the way `ObjectStorageService` etc. are inside the Austial app process.
_ocr_provider = MockOcrProvider()
_liveness_provider = MockLivenessProvider()
_sanctions_provider = MockSanctionsScreeningProvider()


@celery_app.task(name="jobs.kyc.run_ocr_extraction")
def run_ocr_extraction_task(*, document_type: str, object_key: str) -> dict[str, Any]:
    return _ocr_provider.extract(document_type=document_type, object_key=object_key)


@celery_app.task(name="jobs.kyc.run_liveness_face_match")
def run_liveness_face_match_task(
    *, submission_id: int, selfie_object_key: str, id_document_object_key: str
) -> dict[str, Any]:
    return _liveness_provider.verify(
        submission_id=submission_id,
        selfie_object_key=selfie_object_key,
        id_document_object_key=id_document_object_key,
    )


@celery_app.task(name="jobs.kyc.run_sanctions_screening")
def run_sanctions_screening_task(*, legal_name: str, nationality: str) -> dict[str, Any]:
    return _sanctions_provider.screen(legal_name=legal_name, nationality=nationality)


@celery_app.task(name="jobs.kyc.periodic_resanction_screening")
def periodic_resanction_screening_task(*, investor_id: int, legal_name: str, nationality: str) -> dict[str, Any]:
    """Periodic re-screening task *shape* -- same mock provider as the one-time
    ``run_sanctions_screening_task`` above, called on an ``investor_id`` rather than a
    ``submission_id`` since re-screening runs against an already-``VERIFIED`` investor, not a
    pipeline in flight.

    No Celery Beat schedule is registered for this task yet (this app's cost-capped deployment --
    see ``celery_app.py``'s docstring -- has no scheduler process running today); wiring a
    `celery_app.conf.beat_schedule` entry for this task is a small follow-up, not a redesign, once
    a real sanctions provider (Phase 9) makes periodic re-screening worth actually running.
    """
    result = _sanctions_provider.screen(legal_name=legal_name, nationality=nationality)
    return {**result, "investor_id": investor_id}
