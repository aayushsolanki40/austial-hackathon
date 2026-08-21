"""Single source of truth for the app's complete entity list.

``DataSource`` (and, downstream, Alembic's ``target_metadata`` via
``DataSource.get_metadata()`` -- see ``alembic/env.py``) needs the *complete*
schema up front, not just one feature module's ``OrmModule.for_feature([...])``
slice of it. Both ``AppModule`` (the running app) and ``alembic/env.py`` (the
migration tool, run as a separate process outside the app's DI graph) import
``ALL_ENTITIES`` from here so the two can never silently drift apart -- add a
new entity to this one list, not separately in each place.
"""

from __future__ import annotations

from src.modules.assets.entities.asset import Asset
from src.modules.auth.entities.refresh_token import RefreshToken
from src.modules.auth.entities.user import User
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.custodians.entities.custodian import Custodian
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.investors.entities.wallet_mapping import WalletMapping
from src.modules.issuers.entities.issuer import Issuer
from src.modules.kyc.entities.kyc_document import KycDocument
from src.modules.kyc.entities.kyc_submission import KycSubmission
from src.modules.kyc.entities.risk_disclosure_consent import RiskDisclosureConsent

ALL_ENTITIES = [
    User,
    RefreshToken,
    InvestorProfile,
    WalletMapping,
    KycSubmission,
    KycDocument,
    RiskDisclosureConsent,
    AuditLog,
    Issuer,
    Custodian,
    Asset,
]
