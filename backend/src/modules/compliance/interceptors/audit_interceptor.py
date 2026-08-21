"""``AuditInterceptor`` -- Phase 1.6. Global interceptor: appends one
``AuditLog`` row for every mutating (POST/PATCH/PUT/DELETE) request, success
or failure, ``actor_user_id`` sourced from ``request.state.user`` (set by
``JwtAuthGuard`` when present -- guards always run before interceptors in
Austial's request pipeline, so this is safe to read here even though it's
``None`` for unauthenticated mutating routes like ``POST /auth/register``).

Scope note: this interceptor has no domain knowledge of any given entity's
"before" state (that would require a per-route hook this generic, global
interceptor doesn't have), so ``before_state`` is always left ``None`` here.
``after_state`` captures the handler's own response payload on success. A
domain service that needs a real before/after diff for a specific
regulator-sensitive action (e.g. a role change) should write its own
``AuditLog`` row directly via the injected repository, in addition to (not
instead of) this generic one.

Append-only: only ever ``self.audit_logs.save(...)`` here -- see
``AuditLog``'s own docstring.
"""

from __future__ import annotations

from typing import Any

from austial import CallHandler, ExecutionContext, NestInterceptor
from austial.orm import InjectRepository, Repository
from pydantic import BaseModel

from src.i18n.i18n import t
from src.modules.compliance.entities.audit_log import AuditLog

_MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


def _actor_user_id(user: dict | None) -> int | None:
    if not user or "sub" not in user:
        return None
    try:
        return int(user["sub"])
    except (TypeError, ValueError):
        return None


def _entity_type(context: ExecutionContext) -> str:
    class_name = context.get_class().__name__
    return (
        class_name[: -len("Controller")]
        if class_name.endswith("Controller")
        else class_name or t("compliance.audit.unknown_entity_type_label")
    )


def _entity_id(request: Any) -> str | None:
    path_params = dict(request.path_params)
    if "id" in path_params:
        return str(path_params["id"])
    return None


def _serialize(result: Any) -> dict | None:
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if isinstance(result, dict):
        return result
    return None


class AuditInterceptor(NestInterceptor):
    def __init__(self, audit_logs: Repository[AuditLog] = InjectRepository(AuditLog)):
        self.audit_logs = audit_logs

    async def intercept(self, context: ExecutionContext, next: CallHandler) -> Any:
        request = context.get_request()
        if request.method not in _MUTATING_METHODS:
            return await next.handle()

        actor_user_id = _actor_user_id(getattr(request.state, "user", None))
        entity_type = _entity_type(context)
        entity_id = _entity_id(request)
        action = f"{request.method} {request.url.path}"
        ip_address = request.client.host if request.client else None

        try:
            result = await next.handle()
        except Exception:
            await self._save(action, entity_type, entity_id, actor_user_id, ip_address, after_state=None)
            raise

        await self._save(action, entity_type, entity_id, actor_user_id, ip_address, after_state=_serialize(result))
        return result

    async def _save(
        self,
        action: str,
        entity_type: str,
        entity_id: str | None,
        actor_user_id: int | None,
        ip_address: str | None,
        *,
        after_state: dict | None,
    ) -> None:
        await self.audit_logs.save(
            # `# type: ignore[call-arg]` -- see the note on `User(...)` in `AuthService.register()`
            # (`src/modules/auth/auth_service.py`): `austial-py` ships no `py.typed` marker yet, so
            # mypy doesn't apply `@Entity()`'s `dataclass_transform` here either.
            AuditLog(  # type: ignore[call-arg]
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_state=None,
                after_state=after_state,
                ip_address=ip_address,
            )
        )
