"""``OtpModule`` -- Phase 2+. OTP generation/verification with development mode support."""

from __future__ import annotations

from austial import Module
from austial.orm import OrmModule

from src.modules.otp.entities.otp_code import OtpCode
from src.modules.otp.otp_controller import OtpController
from src.modules.otp.otp_service import OtpService


@Module(
    imports=[OrmModule.for_feature([OtpCode])],
    controllers=[OtpController],
    providers=[OtpService],
    exports=[OtpService],
)
class OtpModule:
    pass
