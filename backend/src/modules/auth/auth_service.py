"""``AuthService`` -- Phase 1.2. Registration, login, refresh-token rotation,
and logout, backed by bcrypt password hashing (``passlib``) and JWT
issue/verify (``python-jose``).
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from austial import ConflictException, Injectable, UnauthorizedException
from austial.config import ConfigService
from austial.orm import InjectRepository, Repository
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.i18n.i18n import t
from src.modules.auth.auth_constants import (
    ACCESS_TOKEN_TYPE,
    DEFAULT_ACCESS_TOKEN_TTL_MINUTES,
    DEFAULT_REFRESH_TOKEN_TTL_DAYS,
    JWT_ALGORITHM,
    REFRESH_TOKEN_TYPE,
)
from src.modules.auth.auth_dto import (
    AuthResponseDto,
    LoginDto,
    LogoutDto,
    MessageResponseDto,
    RefreshDto,
    RegisterDto,
    TokenPairDto,
    UserResponseDto,
)
from src.modules.auth.entities.refresh_token import RefreshToken
from src.modules.auth.entities.user import User
from src.modules.investors.entities.investor_profile import InvestorProfile

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_refresh_token(raw_token: str) -> str:
    """Refresh tokens are opaque-enough (structured JWTs, not user-chosen
    secrets) that a fast SHA-256 digest -- rather than bcrypt, which is
    reserved for user passwords -- is the appropriate storage hash: it lets
    ``AuthService.refresh()``/``logout()`` look a presented token up by exact
    hash in O(1), which bcrypt's per-hash random salt would not allow."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@Injectable()
class AuthService:
    def __init__(
        self,
        config: ConfigService,
        users: Repository[User] = InjectRepository(User),
        refresh_tokens: Repository[RefreshToken] = InjectRepository(RefreshToken),
        investor_profiles: Repository[InvestorProfile] = InjectRepository(InvestorProfile),
    ):
        self.config = config
        self.users = users
        self.refresh_tokens = refresh_tokens
        self.investor_profiles = investor_profiles

    # -- public API ----------------------------------------------------------------

    async def register(self, dto: RegisterDto) -> AuthResponseDto:
        existing = await self.users.find_one_by({"email": dto.email})
        if existing is not None:
            raise ConflictException(t("auth.error.email_already_registered"))

        user = await self.users.save(
            # `# type: ignore[call-arg]` -- `austial-py` ships no `py.typed` marker (PEP 561) yet,
            # so mypy doesn't apply `@Entity()`'s `typing.dataclass_transform` for consumers and
            # wrongly flags every keyword-constructed entity here. Framework packaging gap, not an
            # app bug -- flagged for `austial-framework-dev`, not worked around at runtime.
            User(email=dto.email, password_hash=_pwd_context.hash(dto.password), role="INVESTOR")  # type: ignore[call-arg]
        )

        # Auto-create a verified investor profile on registration (bypasses KYC onboarding)
        await self.investor_profiles.save(
            InvestorProfile(  # type: ignore[call-arg]
                user=user,
                investor_type="INDIVIDUAL",  # Default to individual investor
                jurisdiction="IN",  # Default to India (GIFT City jurisdiction)
                risk_profile="MODERATE",  # Default to moderate risk profile
                kyc_status="VERIFIED",  # Auto-verify on registration
            )
        )

        tokens = await self._issue_token_pair(user)
        return AuthResponseDto(user=_to_user_dto(user), tokens=tokens)

    async def login(self, dto: LoginDto) -> AuthResponseDto:
        user = await self.users.find_one_by({"email": dto.email})
        if user is None or not _pwd_context.verify(dto.password, user.password_hash):
            raise UnauthorizedException(t("auth.error.invalid_credentials"))
        if not user.is_active:
            # Phase 1.10 -- `PATCH /admin/users/:id/suspend` sets `is_active=False`; a suspended
            # user must actually be blocked from signing in, not just flagged for display.
            raise UnauthorizedException(t("auth.error.account_suspended"))

        tokens = await self._issue_token_pair(user)
        return AuthResponseDto(user=_to_user_dto(user), tokens=tokens)

    async def refresh(self, dto: RefreshDto) -> TokenPairDto:
        claims = self._decode(dto.refresh_token, expected_type=REFRESH_TOKEN_TYPE)
        stored = await self.refresh_tokens.find_one_by({"token_hash": _hash_refresh_token(dto.refresh_token)})
        if stored is None or stored.revoked or stored.expires_at < datetime.now(UTC).replace(tzinfo=None):
            raise UnauthorizedException(t("auth.error.invalid_refresh_token"))

        user = await self.users.find_one_by({"id": int(claims["sub"])})
        if user is None:
            raise UnauthorizedException(t("auth.error.invalid_refresh_token"))

        # Rotate: revoke the presented refresh token, issue a brand new pair.
        stored.revoked = True
        await self.refresh_tokens.save(stored)
        return await self._issue_token_pair(user)

    async def logout(self, dto: LogoutDto) -> MessageResponseDto:
        stored = await self.refresh_tokens.find_one_by({"token_hash": _hash_refresh_token(dto.refresh_token)})
        if stored is not None and not stored.revoked:
            stored.revoked = True
            await self.refresh_tokens.save(stored)
        # Idempotent either way -- logging out an already-revoked/unknown token isn't an error,
        # it just means "you're already logged out", and we don't want to leak token validity.
        return MessageResponseDto(message=t("auth.logout_success_message"))

    # -- internals -------------------------------------------------------------------

    async def _issue_token_pair(self, user: User) -> TokenPairDto:
        access_ttl = timedelta(
            minutes=int(self.config.get("JWT_ACCESS_TOKEN_TTL_MINUTES", DEFAULT_ACCESS_TOKEN_TTL_MINUTES))
        )
        refresh_ttl = timedelta(days=int(self.config.get("JWT_REFRESH_TOKEN_TTL_DAYS", DEFAULT_REFRESH_TOKEN_TTL_DAYS)))

        access_token, _ = self._encode(user, ACCESS_TOKEN_TYPE, access_ttl)
        refresh_token, refresh_expires_at = self._encode(user, REFRESH_TOKEN_TYPE, refresh_ttl)

        await self.refresh_tokens.save(
            # See the `# type: ignore[call-arg]` note on `User(...)` in `register()` above -- same
            # `austial-py` `py.typed` gap.
            RefreshToken(  # type: ignore[call-arg]
                user=user,
                token_hash=_hash_refresh_token(refresh_token),
                expires_at=refresh_expires_at.replace(tzinfo=None),
                revoked=False,
            )
        )

        return TokenPairDto(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(access_ttl.total_seconds()),
        )

    def _encode(self, user: User, token_type: str, ttl: timedelta) -> tuple[str, datetime]:
        now = datetime.now(UTC)
        expires_at = now + ttl
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
            "type": token_type,
            "iat": now,
            "exp": expires_at,
            # A per-token nonce -- without it, two tokens of the same type issued for
            # the same user within the same wall-clock second (e.g. register
            # immediately followed by login, or back-to-back refreshes) would encode
            # to byte-identical JWTs, colliding on `refresh_token.token_hash`'s unique
            # constraint. `jti` isn't otherwise read/verified today, it exists purely
            # to guarantee token uniqueness.
            "jti": uuid.uuid4().hex,
        }
        token = jwt.encode(payload, self.config.get_or_throw("JWT_SECRET"), algorithm=JWT_ALGORITHM)
        return token, expires_at

    def _decode(self, token: str, *, expected_type: str) -> dict:
        try:
            claims = jwt.decode(token, self.config.get_or_throw("JWT_SECRET"), algorithms=[JWT_ALGORITHM])
        except JWTError as exc:
            raise UnauthorizedException(t("auth.error.invalid_refresh_token")) from exc
        if claims.get("type") != expected_type:
            raise UnauthorizedException(t("auth.error.invalid_refresh_token"))
        return claims


def _to_user_dto(user: User) -> UserResponseDto:
    return UserResponseDto(id=user.id, email=user.email, role=user.role, created_at=user.created_at)
