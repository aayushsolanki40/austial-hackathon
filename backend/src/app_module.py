"""Root application module -- mirrors Nest's ``src/app.module.ts``."""

from austial import Module
from austial.common.middleware import LoggingMiddleware, MiddlewareConsumer
from austial.config import ConfigModule, ConfigService
from austial.orm import OrmModule

from src.app_controller import AppController
from src.app_service import AppService
from src.modules.auth.auth_module import AuthModule
from src.modules.auth.entities.refresh_token import RefreshToken
from src.modules.auth.entities.user import User
from src.modules.compliance.compliance_module import ComplianceModule
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.health.health_module import HealthModule
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.investors.investors_module import InvestorsModule

# Every entity in the app, regardless of which feature module's `OrmModule.for_feature([...])`
# actually injects its repository -- `DataSource` (and, downstream, Alembic's `target_metadata`
# via `DataSource.get_metadata()`) needs the *complete* schema up front, not just one module's
# slice of it.
_ENTITIES = [User, RefreshToken, InvestorProfile, AuditLog]


@Module(
    imports=[
        ConfigModule.for_root(),
        OrmModule.for_root_async(
            use_factory=lambda config: {
                "type_": "postgres",
                "url": config.get_or_throw("DATABASE_URL"),
            },
            inject=[ConfigService],
            entities=_ENTITIES,
        ),
        HealthModule,
        AuthModule,
        InvestorsModule,
        ComplianceModule,
    ],
    controllers=[AppController],
    providers=[AppService],
)
class AppModule:
    def configure(self, consumer: MiddlewareConsumer) -> None:
        consumer.apply(LoggingMiddleware).for_routes("*")
