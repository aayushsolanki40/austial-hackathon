from austial import Module
from austial.orm import OrmModule

from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.kyc.entities.kyc_document import KycDocument
from src.modules.kyc.entities.kyc_submission import KycSubmission
from src.modules.kyc.entities.risk_disclosure_consent import RiskDisclosureConsent
from src.modules.kyc.kyc_controller import KycController
from src.modules.kyc.kyc_service import KycService
from src.storage.storage_module import StorageModule


@Module(
    imports=[
        OrmModule.for_feature([KycSubmission, KycDocument, RiskDisclosureConsent, InvestorProfile]),
        StorageModule,
    ],
    controllers=[KycController],
    providers=[KycService, JwtAuthGuard, RolesGuard],
)
class KycModule:
    pass
