from austial import Module
from austial.orm import OrmModule

from src.modules.admin.admin_controller import AdminController
from src.modules.admin.admin_service import AdminService
from src.modules.auth.entities.user import User
from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.investors.entities.investor_profile import InvestorProfile


@Module(
    imports=[OrmModule.for_feature([User, InvestorProfile, AuditLog])],
    controllers=[AdminController],
    providers=[AdminService, JwtAuthGuard, RolesGuard],
)
class AdminModule:
    pass
