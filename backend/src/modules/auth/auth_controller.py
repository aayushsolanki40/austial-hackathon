from austial import Body, Controller, Post

from src.i18n.i18n import t
from src.modules.auth.auth_dto import (
    AuthResponseDto,
    LoginDto,
    LogoutDto,
    MessageResponseDto,
    RefreshDto,
    RegisterDto,
    TokenPairDto,
)
from src.modules.auth.auth_service import AuthService


@Controller(t("auth.route_prefix"))
class AuthController:
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    @Post("register")
    async def register(self, dto: RegisterDto = Body()) -> AuthResponseDto:
        return await self.auth_service.register(dto)

    @Post("login")
    async def login(self, dto: LoginDto = Body()) -> AuthResponseDto:
        return await self.auth_service.login(dto)

    @Post("refresh")
    async def refresh(self, dto: RefreshDto = Body()) -> TokenPairDto:
        return await self.auth_service.refresh(dto)

    @Post("logout")
    async def logout(self, dto: LogoutDto = Body()) -> MessageResponseDto:
        return await self.auth_service.logout(dto)
