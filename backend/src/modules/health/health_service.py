from austial import Injectable
from austial.terminus import DatabaseHealthIndicator, HealthCheckService, MemoryHealthIndicator

from src.i18n.i18n import t
from src.modules.health.health_dto import HealthResponseDto


@Injectable()
class HealthService:
    def __init__(
        self,
        health_check_service: HealthCheckService,
        memory: MemoryHealthIndicator,
        database: DatabaseHealthIndicator,
    ):
        self.health_check_service = health_check_service
        self.memory = memory
        self.database = database

    async def check(self) -> HealthResponseDto:
        result = await self.health_check_service.check(
            [
                lambda: self.memory.check_heap(t("health.check.memory_heap_label"), 300 * 1024 * 1024),
                lambda: self.database.ping_check(t("health.check.database_label")),
            ]
        )
        return HealthResponseDto(**result)
