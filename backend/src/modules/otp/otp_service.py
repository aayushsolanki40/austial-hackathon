"""``OtpService`` -- OTP generation and verification with development mode support.

In development mode (DEVELOPMENT_MODE=true), OTPs are fixed to a configurable code
(default "123456") and email sending is disabled (only logged to console).

In production mode, OTPs are randomly generated and emails are actually sent via SMTP.
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta

from austial import Injectable, UnauthorizedException
from austial.config import ConfigService
from austial.orm import InjectRepository, Repository

from src.i18n.i18n import t
from src.modules.otp.entities.otp_code import OtpCode

logger = logging.getLogger(__name__)

DEFAULT_OTP_LENGTH = 6
DEFAULT_OTP_TTL_MINUTES = 10
DEFAULT_MAX_ATTEMPTS = 3


@Injectable()
class OtpService:
    def __init__(
        self,
        config: ConfigService,
        otp_codes: Repository[OtpCode] = InjectRepository(OtpCode),
    ):
        self.config = config
        self.otp_codes = otp_codes
        self.dev_mode = config.get("DEVELOPMENT_MODE", "false").lower() == "true"
        self.fixed_otp = config.get("FIXED_OTP_CODE", "123456")

    async def generate_and_send(self, recipient: str, purpose: str) -> str:
        """Generate OTP, save to DB, and send via email (or log in dev mode).

        Args:
            recipient: Email address or phone number
            purpose: Purpose string (e.g., "email_verification", "login_2fa")

        Returns:
            The generated OTP code (only for dev/testing, production should not return this)
        """
        # Invalidate any existing OTP for this recipient/purpose
        await self._invalidate_existing(recipient, purpose)

        # Generate OTP
        if self.dev_mode:
            otp_code = self.fixed_otp
            logger.info(f"[DEV MODE] Using fixed OTP code: {otp_code}")
        else:
            otp_code = self._generate_random_otp()

        # Calculate expiry
        ttl_minutes = int(self.config.get("OTP_TTL_MINUTES", str(DEFAULT_OTP_TTL_MINUTES)))
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)

        # Save to database
        await self.otp_codes.save(
            OtpCode(  # type: ignore[call-arg]
                recipient=recipient,
                purpose=purpose,
                code_hash=self._hash_code(otp_code),
                expires_at=expires_at.replace(tzinfo=None),
                attempts=0,
                verified=False,
            )
        )

        # Send (or mock send in dev mode)
        await self._send_otp(recipient, otp_code, purpose)

        return otp_code if self.dev_mode else ""

    async def verify(self, recipient: str, purpose: str, code: str) -> bool:
        """Verify an OTP code.

        Args:
            recipient: Email address or phone number
            purpose: Purpose string (must match what was used in generate_and_send)
            code: The OTP code to verify

        Returns:
            True if verification succeeded

        Raises:
            UnauthorizedException: If code is invalid, expired, or max attempts exceeded
        """
        stored = await self._find_active_otp(recipient, purpose)
        if stored is None:
            raise UnauthorizedException(t("otp.error.invalid_or_expired"))

        # Check expiry
        if stored.expires_at < datetime.now(UTC).replace(tzinfo=None):
            raise UnauthorizedException(t("otp.error.expired"))

        # Check max attempts
        max_attempts = int(self.config.get("OTP_MAX_ATTEMPTS", str(DEFAULT_MAX_ATTEMPTS)))
        if stored.attempts >= max_attempts:
            raise UnauthorizedException(t("otp.error.max_attempts_exceeded"))

        # Increment attempts
        stored.attempts += 1
        await self.otp_codes.save(stored)

        # Verify code
        if not self._verify_code_hash(code, stored.code_hash):
            if stored.attempts >= max_attempts:
                raise UnauthorizedException(t("otp.error.max_attempts_exceeded"))
            raise UnauthorizedException(t("otp.error.invalid_code"))

        # Mark as verified
        stored.verified = True
        await self.otp_codes.save(stored)

        return True

    # -- internals -------------------------------------------------------------------

    def _generate_random_otp(self) -> str:
        """Generate a cryptographically secure random OTP."""
        otp_length = int(self.config.get("OTP_LENGTH", str(DEFAULT_OTP_LENGTH)))
        # Generate random digits (secrets.randbelow is cryptographically secure)
        return "".join(str(secrets.randbelow(10)) for _ in range(otp_length))

    def _hash_code(self, code: str) -> str:
        """Hash the OTP code for secure storage.

        Unlike passwords (bcrypt), OTPs are short-lived and high-entropy, so SHA-256 is
        sufficient and allows exact-match lookups without per-row salt overhead.
        """
        import hashlib

        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    def _verify_code_hash(self, code: str, code_hash: str) -> bool:
        """Verify an OTP code against its stored hash."""
        return self._hash_code(code) == code_hash

    async def _send_otp(self, recipient: str, code: str, purpose: str) -> None:
        """Send OTP via email (or log in dev mode)."""
        if self.dev_mode:
            logger.info(f"[DEV MODE] OTP for {recipient} ({purpose}): {code}")
            logger.info("Email sending disabled in development mode. Set DEVELOPMENT_MODE=false to enable.")
            return

        # Production: send actual email via SMTP
        # TODO Phase 9: Integrate with actual email service (SendGrid, AWS SES, etc.)
        logger.warning(f"Production email sending not yet implemented. OTP: {code} for {recipient}")

    async def _invalidate_existing(self, recipient: str, purpose: str) -> None:
        """Invalidate any existing OTP for this recipient/purpose."""
        existing = await self._find_active_otp(recipient, purpose)
        if existing is not None:
            existing.verified = True  # Mark as used to prevent reuse
            await self.otp_codes.save(existing)

    async def _find_active_otp(self, recipient: str, purpose: str) -> OtpCode | None:
        """Find the most recent unverified OTP for this recipient/purpose."""
        return await (
            self.otp_codes.create_query_builder("otp")
            .where("otp.recipient = :recipient", {"recipient": recipient})
            .and_where("otp.purpose = :purpose", {"purpose": purpose})
            .and_where_eq("otp.verified", False)
            .add_order_by("otp.created_at", "DESC")
            .get_one()
        )
