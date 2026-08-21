"""Unit tests for the Celery infrastructure seam -- Phase 1.7. ``task_always_eager``
runs tasks synchronously in-process (no live Redis broker needed), keeping this
hermetic like the rest of the suite; the real end-to-end "worker actually consumes
from Redis" path is exercised manually (see ``README.md``'s Celery section), not here.
"""

from __future__ import annotations

from austial.core.metadata import MODULE_METADATA, get_metadata

from src.jobs.celery_app import CELERY_APP_TOKEN, celery_app
from src.jobs.jobs_module import JobsModule
from src.jobs.tasks import health_check_task


def test_celery_app_is_configured_with_json_serialization():
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.conf.timezone == "UTC"


def test_health_check_task_is_registered_on_the_app():
    assert "jobs.health_check" in celery_app.tasks


def test_health_check_task_runs_eagerly_and_returns_ok():
    celery_app.conf.task_always_eager = True
    try:
        result = health_check_task.delay()
        assert result.get(timeout=5) == "ok"
    finally:
        celery_app.conf.task_always_eager = False


def test_health_check_task_callable_directly_returns_ok():
    # The plain-function call path (no broker/result-backend involved at all) -- what a future
    # domain task's own unit test would exercise for its business logic.
    assert health_check_task() == "ok"


def test_jobs_module_registers_celery_app_under_its_di_token():
    metadata = get_metadata(MODULE_METADATA, JobsModule)
    assert metadata.providers[0]["provide"] == CELERY_APP_TOKEN
    assert metadata.providers[0]["useValue"] is celery_app
    assert CELERY_APP_TOKEN in metadata.exports
