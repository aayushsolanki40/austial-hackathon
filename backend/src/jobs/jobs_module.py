"""``JobsModule`` -- Phase 1.7. Makes the already-constructed ``celery_app`` singleton (see
``celery_app.py``) available via the Austial DI container, mirroring how ``ConfigModule``/
``OrmModule`` register an already-built object as a provider (``useValue``) rather than letting
the container construct it.

No user-facing strings here (background/internal infra, not an HTTP-facing module) -- so, per the
workspace i18n convention, no ``src/i18n/locales/en/jobs.json`` is needed.
"""

from austial import Module

from src.jobs.celery_app import CELERY_APP_TOKEN, celery_app


@Module(
    providers=[{"provide": CELERY_APP_TOKEN, "useValue": celery_app}],
    exports=[CELERY_APP_TOKEN],
)
class JobsModule:
    pass
