"""``OtpCode`` entity -- stores OTP verification codes with expiry and attempt tracking."""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, PrimaryGeneratedColumn


@Entity()
class OtpCode:
    """OTP verification code record.

    One row per generated OTP. Not reused -- each ``generate_and_send()`` call creates
    a fresh row and marks any previous unverified OTP for the same recipient/purpose as used.

    Fields:
        recipient: Email address or phone number receiving the OTP
        purpose: Purpose identifier (e.g., "email_verification", "login_2fa")
        code_hash: SHA-256 hash of the OTP code (not stored in plaintext)
        expires_at: Expiration timestamp (typically 10 minutes from creation)
        attempts: Number of verification attempts made
        verified: Whether this OTP has been successfully verified (or invalidated)
        created_at: When this OTP was generated
    """

    id: int = PrimaryGeneratedColumn()
    recipient: str = Column()
    purpose: str = Column()
    code_hash: str = Column()
    expires_at: datetime = Column()
    attempts: int = Column(default=0)
    verified: bool = Column(default=False)
    created_at: datetime = CreateDateColumn()
