from austial import Module
from austial.orm import OrmModule

from src.modules.compliance.compliance_controller import ComplianceController
from src.modules.compliance.compliance_service import ComplianceService
from src.modules.compliance.entities.aml_alert import AmlAlert
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.compliance.entities.compliance_report import ComplianceReport
from src.modules.compliance.interceptors.audit_interceptor import AuditInterceptor


@Module(
    imports=[OrmModule.for_feature([AuditLog, AmlAlert, ComplianceReport])],
    controllers=[ComplianceController],
    providers=[AuditInterceptor, ComplianceService],
    exports=[AuditInterceptor, ComplianceService],
)
class ComplianceModule:
    pass
