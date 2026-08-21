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
from src.modules.holdings.entities.token_holding import TokenHolding
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.investors.entities.wallet_mapping import WalletMapping
from src.modules.issuance.entities.disclosure_document import DisclosureDocument
from src.modules.issuance.entities.smart_contract_deployment import SmartContractDeployment
from src.modules.issuance.entities.token_series import TokenSeries
from src.modules.issuance.entities.tokenization_proposal import TokenizationProposal
from src.modules.issuers.entities.issuer import Issuer
from src.modules.kyc.entities.kyc_document import KycDocument
from src.modules.kyc.entities.kyc_submission import KycSubmission
from src.modules.kyc.entities.risk_disclosure_consent import RiskDisclosureConsent
from src.modules.ledger.entities.funding_instruction import FundingInstruction
from src.modules.ledger.entities.ledger_account import LedgerAccount
from src.modules.ledger.entities.ledger_entry import LedgerEntry
from src.modules.ledger.entities.payout_instruction import PayoutInstruction
from src.modules.subscriptions.entities.subscription import Subscription

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
    TokenizationProposal,
    DisclosureDocument,
    SmartContractDeployment,
    TokenSeries,
    LedgerAccount,
    LedgerEntry,
    FundingInstruction,
    PayoutInstruction,
    Subscription,
    TokenHolding,
]
