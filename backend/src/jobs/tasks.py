"""Phase 1.7 placeholder task -- proves the worker boots and can execute a task end-to-end.
Not a domain job body; Phase 2+ tasks (sanctions re-screening, valuation polling, etc.) get their
own modules under here once that domain logic exists.
"""

from __future__ import annotations

from src.jobs.celery_app import celery_app


@celery_app.task(name="jobs.health_check")
def health_check_task() -> str:
    return "ok"
