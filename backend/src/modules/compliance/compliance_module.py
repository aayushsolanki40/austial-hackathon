from austial import Module
from austial.orm import OrmModule

from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.compliance.interceptors.audit_interceptor import AuditInterceptor


@Module(
    imports=[OrmModule.for_feature([AuditLog])],
    providers=[AuditInterceptor],
    exports=[AuditInterceptor],
)
class ComplianceModule:
    pass
