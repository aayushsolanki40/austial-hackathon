from austial import Module
from austial.orm import OrmModule, repository_token

from src.modules.auth.guards.jwt_auth_guard import JwtAuthGuard
from src.modules.auth.guards.roles_guard import RolesGuard
from src.modules.investors.investors_module import InvestorsModule
from src.modules.ledger.entities.funding_instruction import FundingInstruction
from src.modules.ledger.entities.ledger_account import LedgerAccount
from src.modules.ledger.entities.ledger_entry import LedgerEntry
from src.modules.ledger.entities.payout_instruction import PayoutInstruction
from src.modules.ledger.ledger_controller import LedgerController
from src.modules.ledger.ledger_service import LedgerService


@Module(
    imports=[
        OrmModule.for_feature([LedgerAccount, LedgerEntry, FundingInstruction, PayoutInstruction]),
        InvestorsModule,
    ],
    controllers=[LedgerController],
    providers=[LedgerService, JwtAuthGuard, RolesGuard],
    exports=[repository_token(LedgerAccount), repository_token(LedgerEntry)],
)
class LedgerModule:
    pass
