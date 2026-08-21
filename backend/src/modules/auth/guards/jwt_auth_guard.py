"""``JwtAuthGuard`` -- Phase 1.3.

Parses ``Authorization: Bearer <token>``, verifies it via ``python-jose``,
and attaches the decoded claims to ``request.state.user`` for downstream
guards (``RolesGuard``, ``KycVerifiedGuard``) and route handlers to read.
Must run *before* those guards in a route's ``@UseGuards(...)`` chain --
Austial's router builder always evaluates guards in the order they're
listed (global, then controller-level, then handler-level; see
``austial-py``'s ``RouterBuilder._resolve_chain``), so simply listing
``JwtAuthGuard`` first is sufficient.
"""

from __future__ import annotations

from austial import CanActivate, ExecutionContext, UnauthorizedException
from austial.config import ConfigService
from jose import JWTError, jwt

from src.i18n.i18n import t
from src.modules.auth.auth_constants import ACCESS_TOKEN_TYPE, JWT_ALGORITHM


class JwtAuthGuard(CanActivate):
    """Demo-guard-style ``CanActivate`` -- mirrors the project's existing
    ``ApiKeyGuard`` (``src/modules/health/guards/api_key_guard.py``): a plain
    undecorated class, constructor-injected via the DI container when passed
    as a class to ``@UseGuards(...)``."""

    def __init__(self, config: ConfigService):
        self.config = config

    async def can_activate(self, context: ExecutionContext) -> bool:
        request = context.get_request()
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise UnauthorizedException(t("auth.error.not_authenticated"))

        try:
            claims = jwt.decode(token, self.config.get_or_throw("JWT_SECRET"), algorithms=[JWT_ALGORITHM])
        except JWTError as exc:
            raise UnauthorizedException(t("auth.error.invalid_or_expired_token")) from exc

        if claims.get("type") != ACCESS_TOKEN_TYPE:
            raise UnauthorizedException(t("auth.error.invalid_or_expired_token"))

        request.state.user = claims
        return True
