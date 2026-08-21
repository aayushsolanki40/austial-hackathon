"""Unit tests for ``RedemptionsService`` -- Phase 7. Exercises the redemption-request state
machine (illegal-jump rejection, unit-quantity validation), NAV snapshotting on approval,
``complete``'s atomic ledger-credit + payout-debit + holding-shrink, and the pro-rata
distribution engine's remainder handling. Mirrors ``subscriptions_service_spec.py``'s
in-memory-SQLite seeding pattern, seeding a ``TokenHolding`` directly since only Phase 7
behaviour is under test here.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from austial import ConflictException, UnprocessableEntityException
from austial.config import ConfigService
from austial.orm import DataSource, OrmModule, repository_token
from austial.testing import Test

from src.modules.assets.entities.asset import Asset
from src.modules.auth.entities.user import User
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.custodians.entities.custodian import Custodian
from src.modules.holdings.entities.token_holding import TokenHolding
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.issuance.entities.smart_contract_deployment import SmartContractDeployment
from src.modules.issuance.entities.token_series import TokenSeries
from src.modules.issuance.entities.tokenization_proposal import TokenizationProposal
from src.modules.issuers.entities.issuer import Issuer
from src.modules.ledger.entities.funding_instruction import FundingInstruction
from src.modules.ledger.entities.ledger_account import LedgerAccount
from src.modules.ledger.entities.ledger_entry import LedgerEntry
from src.modules.ledger.entities.payout_instruction import PayoutInstruction
from src.modules.ledger.ledger_service import LedgerService
from src.modules.redemptions.entities.distribution import Distribution
from src.modules.redemptions.entities.redemption_request import RedemptionRequest
from src.modules.redemptions.redemptions_dto import CreateDistributionDto, CreateRedemptionRequestDto
from src.modules.redemptions.redemptions_service import RedemptionsService
from src.modules.valuation.entities.valuation_feed import ValuationFeed
from src.modules.valuation.valuation_service import ValuationService

_NOW = datetime.now(UTC).replace(tzinfo=None)

_ENTITIES = [
    User,
    InvestorProfile,
    Issuer,
    Custodian,
    Asset,
    TokenizationProposal,
    TokenSeries,
    SmartContractDeployment,
    LedgerAccount,
    LedgerEntry,
    FundingInstruction,
    PayoutInstruction,
    TokenHolding,
    ValuationFeed,
    RedemptionRequest,
    Distribution,
    AuditLog,
]


async def _build_module():
    module = await Test.create_testing_module(
        imports=[
            OrmModule.for_root(
                type_="sqlite", url="sqlite+aiosqlite:///:memory:", entities=_ENTITIES, synchronize=True
            ),
            OrmModule.for_feature(_ENTITIES),
        ],
        providers=[
            RedemptionsService,
            LedgerService,
            ValuationService,
            {
                "provide": ConfigService,
                "useValue": ConfigService(
                    {
                        "LEDGER_BENEFICIARY_NAME": "Test",
                        "LEDGER_BENEFICIARY_BANK_NAME": "Test Bank",
                        "LEDGER_BENEFICIARY_ACCOUNT_NUMBER": "000123456789",
                        "LEDGER_BENEFICIARY_SWIFT_BIC": "TESTINBBXXX",
                    }
                ),
            },
        ],
    ).compile()
    await module.get(DataSource).initialize()
    return module


async def _seed_series(module, *, unit_price: float = 100) -> TokenSeries:
    users = module.get(repository_token(User))
    issuers = module.get(repository_token(Issuer))
    assets = module.get(repository_token(Asset))
    proposals = module.get(repository_token(TokenizationProposal))
    series_repo = module.get(repository_token(TokenSeries))

    issuer_user = await users.save(User(email=f"issuer-{id(module)}@x.com", password_hash="x", role="ISSUER"))  # type: ignore[call-arg]
    issuer = await issuers.save(
        Issuer(user=issuer_user, legal_name="Acme", registration_number="R1", registration_jurisdiction="in")  # type: ignore[call-arg]
    )
    asset = await assets.save(Asset(issuer=issuer, name="Tower A", asset_class="REAL_ESTATE"))  # type: ignore[call-arg]
    proposal = await proposals.save(
        TokenizationProposal(  # type: ignore[call-arg]
            asset=asset,
            issuer=issuer,
            total_units=1000,
            unit_price_usd=unit_price,
            min_subscription_units=10,
            status="LAUNCHED",
            subscription_start_at=_NOW - timedelta(days=10),
            subscription_end_at=_NOW - timedelta(days=1),
        )
    )
    series = await series_repo.save(
        TokenSeries(proposal=proposal, symbol=f"SYM{id(module) % 100000}", total_supply=1000, paused=False)  # type: ignore[call-arg]
    )
    series.proposal = proposal
    return series


async def _seed_investor_with_holding(
    module, series: TokenSeries, *, email: str, quantity: float = 100, avg_cost: float = 100
) -> tuple[User, InvestorProfile, TokenHolding]:
    users = module.get(repository_token(User))
    investors = module.get(repository_token(InvestorProfile))
    holdings = module.get(repository_token(TokenHolding))

    user = await users.save(User(email=email, password_hash="x", role="INVESTOR"))  # type: ignore[call-arg]
    investor = await investors.save(InvestorProfile(user=user, kyc_status="VERIFIED"))  # type: ignore[call-arg]
    holding = await holdings.save(
        TokenHolding(investor=investor, token_series=series, quantity=quantity, avg_cost_usd=avg_cost, status="ACTIVE")  # type: ignore[call-arg]
    )
    holding.investor = investor
    holding.token_series = series
    return user, investor, holding


def _request_dto(holding_id: int, units: float) -> CreateRedemptionRequestDto:
    return CreateRedemptionRequestDto(holding_id=holding_id, units_requested=units)


@pytest.mark.asyncio
async def test_create_request_rejects_units_exceeding_holding_quantity():
    module = await _build_module()
    service = module.get(RedemptionsService)
    series = await _seed_series(module)
    user, _, holding = await _seed_investor_with_holding(module, series, email="i1@x.com", quantity=100)

    with pytest.raises(UnprocessableEntityException):
        await service.create_request(user.id, _request_dto(holding.id, 150))


@pytest.mark.asyncio
async def test_create_request_rejects_a_non_active_holding():
    module = await _build_module()
    service = module.get(RedemptionsService)
    series = await _seed_series(module)
    user, _, holding = await _seed_investor_with_holding(module, series, email="i2@x.com", quantity=100)
    holdings = module.get(repository_token(TokenHolding))
    await holdings.update({"id": holding.id}, {"status": "FROZEN"})

    with pytest.raises(ConflictException):
        await service.create_request(user.id, _request_dto(holding.id, 10))


@pytest.mark.asyncio
async def test_illegal_transition_raises_conflict():
    module = await _build_module()
    service = module.get(RedemptionsService)
    series = await _seed_series(module)
    user, _, holding = await _seed_investor_with_holding(module, series, email="i3@x.com", quantity=100)

    request = await service.create_request(user.id, _request_dto(holding.id, 40))
    # Cannot release/complete a request that is still just REQUESTED -- only COMPLIANCE_APPROVED
    # can move to CUSTODIAN_RELEASED, per ALLOWED_TRANSITIONS.
    with pytest.raises(ConflictException):
        await service.release(officer_id=99, request_id=request.id)


@pytest.mark.asyncio
async def test_approve_snapshots_nav_and_payout_amount():
    module = await _build_module()
    service = module.get(RedemptionsService)
    series = await _seed_series(module, unit_price=100)
    user, _, holding = await _seed_investor_with_holding(module, series, email="i4@x.com", quantity=100)

    request = await service.create_request(user.id, _request_dto(holding.id, 40))
    approved = await service.approve(officer_id=99, request_id=request.id)

    assert approved.status == "COMPLIANCE_APPROVED"
    assert approved.nav_per_unit_snapshot == 100.0  # falls back to proposal.unit_price_usd, no feed yet
    assert approved.payout_amount == 4000.0


@pytest.mark.asyncio
async def test_complete_settles_ledger_and_shrinks_holding_to_redeemed_on_full_redemption():
    module = await _build_module()
    service = module.get(RedemptionsService)
    series = await _seed_series(module, unit_price=100)
    user, _, holding = await _seed_investor_with_holding(module, series, email="i5@x.com", quantity=100)

    request = await service.create_request(user.id, _request_dto(holding.id, 100))
    await service.approve(officer_id=99, request_id=request.id)
    await service.release(officer_id=99, request_id=request.id)
    completed = await service.complete(officer_id=99, request_id=request.id)

    assert completed.status == "COMPLETED"
    assert completed.payout_amount == 10000.0
    assert completed.payout_instruction_id is not None

    holdings = module.get(repository_token(TokenHolding))
    refreshed_holding = await holdings.find_one_by({"id": holding.id})
    assert float(refreshed_holding.quantity) == 0
    assert refreshed_holding.status == "REDEEMED"

    entries = module.get(repository_token(LedgerEntry))
    all_entries = await entries.find()
    credits = [e for e in all_entries if e.entry_type == "CREDIT_REDEMPTION"]
    debits = [e for e in all_entries if e.entry_type == "DEBIT_PAYOUT"]
    assert len(credits) == 1 and float(credits[0].amount) == 10000.0
    assert len(debits) == 1 and float(debits[0].amount) == 10000.0

    accounts = module.get(repository_token(LedgerAccount))
    account = (await accounts.find())[0]
    # Credited in then immediately debited back out -- net zero balance change.
    assert float(account.available_balance) == 0


@pytest.mark.asyncio
async def test_process_distribution_pro_rata_with_remainder_absorbed_by_last_holder():
    module = await _build_module()
    service = module.get(RedemptionsService)
    series = await _seed_series(module)
    # 3 holders of 1 unit each (33.33 recurring split of $100) -- exercises the ROUND_DOWN +
    # last-holder-absorbs-the-remainder rule so sum(shares) == total_amount exactly.
    await _seed_investor_with_holding(module, series, email="d1@x.com", quantity=1)
    await _seed_investor_with_holding(module, series, email="d2@x.com", quantity=1)
    await _seed_investor_with_holding(module, series, email="d3@x.com", quantity=1)

    distribution = await service.create_distribution(
        officer_id=99,
        dto=CreateDistributionDto(token_series_id=series.id, total_amount=100, currency="USD", record_date=_NOW),
    )
    result = await service.process_distribution(officer_id=99, distribution_id=distribution.id)

    assert result.holder_count == 3
    assert result.total_credited == 100.0

    entries = module.get(repository_token(LedgerEntry))
    credits = [e for e in await entries.find() if e.entry_type == "CREDIT_DISTRIBUTION"]
    assert len(credits) == 3
    assert sum(float(e.amount) for e in credits) == 100.0
    # First two holders get the ROUND_DOWN'd floor share; the third (last, id-ascending) absorbs
    # whatever's left so the three shares sum exactly to total_amount.
    amounts = sorted(float(e.amount) for e in credits)
    assert amounts[0] == amounts[1] == 33.33
    assert amounts[2] == 33.34


@pytest.mark.asyncio
async def test_process_distribution_rejects_a_series_with_no_active_holders():
    module = await _build_module()
    service = module.get(RedemptionsService)
    series = await _seed_series(module)

    distribution = await service.create_distribution(
        officer_id=99,
        dto=CreateDistributionDto(token_series_id=series.id, total_amount=100, currency="USD", record_date=_NOW),
    )
    with pytest.raises(ConflictException):
        await service.process_distribution(officer_id=99, distribution_id=distribution.id)
