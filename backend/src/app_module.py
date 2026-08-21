"""Root application module -- mirrors Nest's ``src/app.module.ts``."""

from austial import Module
from austial.common.middleware import LoggingMiddleware, MiddlewareConsumer
from austial.config import ConfigModule, ConfigService
from austial.orm import OrmModule

from src.app_controller import AppController
from src.app_service import AppService
from src.modules.health.health_module import HealthModule


@Module(
    imports=[
        ConfigModule.for_root(),
        OrmModule.for_root_async(
            use_factory=lambda config: {
                "type_": "postgres",
                "url": config.get_or_throw("DATABASE_URL"),
            },
            inject=[ConfigService],
            entities=[],
        ),
        HealthModule,
    ],
    controllers=[AppController],
    providers=[AppService],
)
class AppModule:
    def configure(self, consumer: MiddlewareConsumer) -> None:
        consumer.apply(LoggingMiddleware).for_routes("*")
