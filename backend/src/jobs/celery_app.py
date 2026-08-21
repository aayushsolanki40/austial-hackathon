"""``celery_app`` -- Phase 1.7 infrastructure seam: one ``Celery`` instance backed by Redis,
proving the app can boot a background-job worker end-to-end. **No Phase 2+ domain job bodies
live here** (sanctions re-screening, valuation polling, etc. don't exist as domain logic yet --
see ``AUSTIAL_BUILD_PLAN.md``); this module + ``tasks.py``'s one placeholder task exist purely
to wire the seam future phases will hang real tasks off of.

Deployment shape (see ``austial-hackathon/infra/terraform/README.md``'s cost ceiling): this app
runs on a single cost-capped ``t3.micro`` EC2 instance with no managed Redis/ElastiCache -- Redis
runs as an additional plain Docker container on that same instance (or, for local dev, as the
``redis`` service in ``docker-compose.yml`` at the repo root). So the broker/backend URL always
points at a container hostname (``redis:6379`` under Docker networking), never ``localhost`` or
an AWS-managed endpoint.

**Env var convention** (picked here, documented so it doesn't drift): a single ``REDIS_URL``
backs *both* the Celery broker and the result backend, since Phase 1 has exactly one Redis
instance and no reason yet to split them onto separate stores. ``CELERY_BROKER_URL`` /
``CELERY_RESULT_BACKEND`` are supported as optional overrides (read first, if set) for the day a
future phase *does* want to split them -- but for now, just set ``REDIS_URL`` and both resolve to
it.

This module is imported directly by the ``celery`` CLI (``celery -A src.jobs.celery_app worker``)
as well as by ``JobsModule`` for in-process DI -- that entrypoint never builds the app's DI graph
via ``ConfigModule``/``ConfigService``, so, like ``ConfigModule.for_root()`` itself, env vars are
read directly here (with the same best-effort ``.env`` loading) rather than requiring the full
Austial app to be constructed first.
"""

from __future__ import annotations

import os

from celery import Celery

try:
    from dotenv import load_dotenv

    load_dotenv(".env", override=False)
except ImportError:  # pragma: no cover - python-dotenv ships transitively today, mirrors ConfigModule
    pass

_DEFAULT_REDIS_URL = "redis://redis:6379/0"

_redis_url = os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
_broker_url = os.environ.get("CELERY_BROKER_URL", _redis_url)
_result_backend = os.environ.get("CELERY_RESULT_BACKEND", _redis_url)

celery_app = Celery(
    "swadely",
    broker=_broker_url,
    backend=_result_backend,
    include=["src.jobs.tasks", "src.jobs.kyc_tasks", "src.jobs.compliance_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# DI token `JobsModule` registers `celery_app` under, for anything that needs to enqueue a task
# from inside the Austial app's own DI container (mirrors `repository_token(...)`'s "string/class
# token, not a real injectable class" pattern -- see `austial.orm.repository_token`).
CELERY_APP_TOKEN = "CELERY_APP"
