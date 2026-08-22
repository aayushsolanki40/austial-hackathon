"""DTOs for OTP generation and verification."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateOtpDto(BaseModel):
    """Request to generate and send an OTP."""

    recipient: str = Field(..., description="Email address or phone number")
    purpose: str = Field(..., description="Purpose (e.g., 'email_verification', 'login_2fa')")


class VerifyOtpDto(BaseModel):
    """Request to verify an OTP."""

    recipient: str = Field(..., description="Email address or phone number")
    purpose: str = Field(..., description="Purpose (must match generation)")
    code: str = Field(..., description="The OTP code to verify")


class OtpResponseDto(BaseModel):
    """Response after OTP generation (dev mode only)."""

    message: str
    dev_otp_code: str | None = Field(
        None, description="Only populated in development mode for testing convenience"
    )


class VerifyOtpResponseDto(BaseModel):
    """Response after OTP verification."""

    verified: bool
    message: str
