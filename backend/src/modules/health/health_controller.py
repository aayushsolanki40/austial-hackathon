from austial import Controller, Get, UseGuards

from src.i18n.i18n import t
from src.modules.health.guards.api_key_guard import ApiKeyGuard
from src.modules.health.health_dto import HealthResponseDto
from src.modules.health.health_service import HealthService


@Controller(t("health.route_prefix"))
class HealthController:
    def __init__(self, health_service: HealthService):
        self.health_service = health_service

    @Get()
    async def check(self) -> HealthResponseDto:
        return await self.health_service.check()

    @Get(t("health.protected_route_path"))
    @UseGuards(ApiKeyGuard)
    async def protected(self):
        return {"message": t("health.protected_message")}
