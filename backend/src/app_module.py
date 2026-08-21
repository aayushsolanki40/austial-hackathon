"""Root application module -- mirrors Nest's ``src/app.module.ts``."""

from austial import Module
from austial.common.middleware import LoggingMiddleware, MiddlewareConsumer
from austial.config import ConfigModule, ConfigService
from austial.orm import OrmModule

from src.app_controller import AppController
from src.app_service import AppService
from src.db.entities import ALL_ENTITIES
from src.jobs.jobs_module import JobsModule
from src.modules.admin.admin_module import AdminModule
from src.modules.auth.auth_module import AuthModule
from src.modules.compliance.compliance_module import ComplianceModule
from src.modules.health.health_module import HealthModule
from src.modules.investors.investors_module import InvestorsModule
from src.storage.storage_module import StorageModule


@Module(
    imports=[
        ConfigModule.for_root(),
        # `synchronize=False` (explicit, not just the default) -- Phase 1.1's `alembic/`
        # migrations own schema creation/evolution now; boot-time `CREATE TABLE` sync would
        # actively fight the migration history, not just be redundant. Tests still use
        # `synchronize=True` against a disposable in-memory SQLite `DataSource` -- see
        # `tests/*/`'s specs -- which isn't the same thing as this real app boot path.
        OrmModule.for_root_async(
            use_factory=lambda config: {
                "type_": "postgres",
                "url": config.get_or_throw("DATABASE_URL"),
            },
            inject=[ConfigService],
            entities=ALL_ENTITIES,
            synchronize=False,
        ),
        HealthModule,
        AuthModule,
        InvestorsModule,
        ComplianceModule,
        JobsModule,
        StorageModule,
        AdminModule,
    ],
    controllers=[AppController],
    providers=[AppService],
)
class AppModule:
    def configure(self, consumer: MiddlewareConsumer) -> None:
        consumer.apply(LoggingMiddleware).for_routes("*")
