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

    # TEMPORARY: Bootstrap endpoint for demo purposes
    @Post("bootstrap-demo-roles")
    async def bootstrap_demo_roles(self) -> dict:
        """
        TEMPORARY endpoint to fix demo user roles without database access.
        Solves the chicken-and-egg admin bootstrap problem.
        TODO: Remove after demo roles are properly seeded.
        """
        from austial.orm import Repository
        from src.modules.auth.entities.user import User
        from src.db.session import get_db_session

        async with get_db_session() as session:
            user_repo = Repository[User](User, session)

            demo_role_map = {
                "admin@demo.swadely.com": "ADMIN",
                "compliance@demo.swadely.com": "COMPLIANCE_OFFICER",
                "issuer1@demo.swadely.com": "ISSUER",
                "issuer2@demo.swadely.com": "ISSUER",
            }

            updated_count = 0
            for email, role in demo_role_map.items():
                user = await user_repo.find_one({"where": {"email": email}})
                if user and user.role != role:
                    user.role = role
                    await user_repo.save(user)
                    updated_count += 1

            await session.commit()

            return {
                "message": "Demo user roles updated successfully",
                "updated_count": updated_count,
                "note": "This endpoint should be removed in production",
            }
