"""``OtpController`` -- OTP generation and verification endpoints.

These are utility endpoints for development/testing. In production, OTP generation
is typically triggered by other flows (registration, login, etc.) rather than
called directly by the client.
"""

from __future__ import annotations

from austial import Body, Controller, Post

from src.i18n.i18n import t
from src.modules.otp.otp_dto import (
    GenerateOtpDto,
    OtpResponseDto,
    VerifyOtpDto,
    VerifyOtpResponseDto,
)
from src.modules.otp.otp_service import OtpService


@Controller(t("otp.route_prefix"))
class OtpController:
    def __init__(self, otp_service: OtpService):
        self.otp_service = otp_service

    @Post("generate")
    async def generate_otp(self, dto: GenerateOtpDto = Body()) -> OtpResponseDto:
        """Generate and send an OTP.

        In development mode, returns the OTP code in the response for testing convenience.
        In production, only sends the email and returns a success message.
        """
        dev_code = await self.otp_service.generate_and_send(dto.recipient, dto.purpose)
        return OtpResponseDto(
            message=t("otp.generated_success"),
            dev_otp_code=dev_code if self.otp_service.dev_mode else None,
        )

    @Post("verify")
    async def verify_otp(self, dto: VerifyOtpDto = Body()) -> VerifyOtpResponseDto:
        """Verify an OTP code."""
        await self.otp_service.verify(dto.recipient, dto.purpose, dto.code)
        return VerifyOtpResponseDto(verified=True, message=t("otp.verified_success"))
