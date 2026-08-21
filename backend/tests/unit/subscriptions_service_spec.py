"""Unit tests for ``SubscriptionsService`` -- Phase 6. Exercises the
``PENDING -> FUNDED -> CONFIRMED -> ALLOCATED`` state machine, fund-locking on subscribe,
the disclosure-acknowledgment gate, and the pro-rata allocation engine. Mirrors
``issuance_service_spec.py``'s in-memory-SQLite pattern, bypassing ``IssuanceService`` and
seeding a ``LAUNCHED`` proposal/``TokenSeries`` directly since only Phase 6 behaviour is
under test here.
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
from src.modules.issuance.entities.disclosure_document import DisclosureDocument
from src.modules.issuance.entities.smart_contract_deployment import SmartContractDeployment
from src.modules.issuance.entities.token_series import TokenSeries
from src.modules.issuance.entities.tokenization_proposal import TokenizationProposal
from src.modules.issuers.entities.issuer import Issuer
from src.modules.ledger.entities.funding_instruction import FundingInstruction
from src.modules.ledger.entities.ledger_account import LedgerAccount
from src.modules.ledger.entities.ledger_entry import LedgerEntry
from src.modules.ledger.entities.payout_instruction import PayoutInstruction
from src.modules.ledger.ledger_service import LedgerService
from src.modules.subscriptions.entities.subscription import Subscription
from src.modules.subscriptions.subscriptions_dto import CreateSubscriptionDto
from src.modules.subscriptions.subscriptions_service import SubscriptionsService

_NOW = datetime.now(UTC).replace(tzinfo=None)
_OPEN_WINDOW = {"subscription_start_at": _NOW - timedelta(days=1), "subscription_end_at": _NOW + timedelta(days=6)}
_CLOSED_WINDOW = {"subscription_start_at": _NOW - timedelta(days=10), "subscription_end_at": _NOW - timedelta(days=1)}

_ENTITIES = [
    User,
    InvestorProfile,
    Issuer,
    Custodian,
    Asset,
    TokenizationProposal,
    DisclosureDocument,
    TokenSeries,
    SmartContractDeployment,
    LedgerAccount,
    LedgerEntry,
    FundingInstruction,
    PayoutInstruction,
    Subscription,
    TokenHolding,
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
            SubscriptionsService,
            LedgerService,
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


async def _seed_series(
    module, *, window: dict, total_units: float = 1000, unit_price: float = 100, min_units: float = 10
):
    users = module.get(repository_token(User))
    issuers = module.get(repository_token(Issuer))
    assets = module.get(repository_token(Asset))
    proposals = module.get(repository_token(TokenizationProposal))
    series_repo = module.get(repository_token(TokenSeries))

    issuer_user = await users.save(User(email=f"issuer-{id(window)}@x.com", password_hash="x", role="ISSUER"))  # type: ignore[call-arg]
    issuer = await issuers.save(
        Issuer(user=issuer_user, legal_name="Acme", registration_number="R1", registration_jurisdiction="in")  # type: ignore[call-arg]
    )
    asset = await assets.save(Asset(issuer=issuer, name="Tower A", asset_class="REAL_ESTATE"))  # type: ignore[call-arg]
    proposal = await proposals.save(
        TokenizationProposal(  # type: ignore[call-arg]
            asset=asset,
            issuer=issuer,
            total_units=total_units,
            unit_price_usd=unit_price,
            min_subscription_units=min_units,
            status="LAUNCHED",
            **window,
        )
    )
    series = await series_repo.save(
        TokenSeries(proposal=proposal, symbol=f"SYM{id(window) % 100000}", total_supply=total_units, paused=False)  # type: ignore[call-arg]
    )
    return proposal, series


async def _seed_investor(module, *, email: str, available_balance: float = 0):
    users = module.get(repository_token(User))
    investors = module.get(repository_token(InvestorProfile))
    accounts = module.get(repository_token(LedgerAccount))
    user = await users.save(User(email=email, password_hash="x", role="INVESTOR"))  # type: ignore[call-arg]
    investor = await investors.save(InvestorProfile(user=user, kyc_status="VERIFIED"))  # type: ignore[call-arg]
    await accounts.save(
        LedgerAccount(investor=investor, currency="USD", available_balance=available_balance, locked_balance=0)  # type: ignore[call-arg]
    )
    return user, investor


def _subscribe_dto(series_id: int, units: float) -> CreateSubscriptionDto:
    return CreateSubscriptionDto(
        token_series_id=series_id, units=units, risk_disclosure_accepted=True, fee_disclosure_accepted=True
    )


async def _close_window(module, proposal_id: int) -> None:
    """Moves a proposal's subscription window into the past -- used to simulate "the window has
    since closed" after subscribing during an open window, since ``subscribe`` requires the
    window open and ``allocate`` requires it closed."""
    proposals = module.get(repository_token(TokenizationProposal))
    await proposals.update({"id": proposal_id}, {"subscription_end_at": _NOW - timedelta(minutes=1)})


@pytest.mark.asyncio
async def test_subscribe_locks_funds_and_creates_pending_subscription():
    module = await _build_module()
    service = module.get(SubscriptionsService)
    _, series = await _seed_series(module, window=_OPEN_WINDOW)
    user, _ = await _seed_investor(module, email="i1@x.com", available_balance=50000)

    sub = await service.subscribe(user.id, _subscribe_dto(series.id, 100))
    assert sub.status == "PENDING"
    assert sub.amount_usd == 10000
    assert sub.disclosures_acknowledged_at is not None

    accounts = module.get(repository_token(LedgerAccount))
    account = (await accounts.find())[0]
    assert float(account.available_balance) == 40000
    assert float(account.locked_balance) == 10000


@pytest.mark.asyncio
async def test_subscribe_rejects_insufficient_balance():
    module = await _build_module()
    service = module.get(SubscriptionsService)
    _, series = await _seed_series(module, window=_OPEN_WINDOW)
    user, _ = await _seed_investor(module, email="i2@x.com", available_balance=500)

    with pytest.raises(UnprocessableEntityException):
        await service.subscribe(user.id, _subscribe_dto(series.id, 100))


@pytest.mark.asyncio
async def test_subscribe_rejects_below_minimum():
    module = await _build_module()
    service = module.get(SubscriptionsService)
    _, series = await _seed_series(module, window=_OPEN_WINDOW, min_units=50)
    user, _ = await _seed_investor(module, email="i3@x.com", available_balance=50000)

    with pytest.raises(UnprocessableEntityException):
        await service.subscribe(user.id, _subscribe_dto(series.id, 10))


@pytest.mark.asyncio
async def test_subscribe_rejects_when_disclosures_not_accepted():
    module = await _build_module()
    service = module.get(SubscriptionsService)
    _, series = await _seed_series(module, window=_OPEN_WINDOW)
    user, _ = await _seed_investor(module, email="i4@x.com", available_balance=50000)

    dto = CreateSubscriptionDto(
        token_series_id=series.id, units=100, risk_disclosure_accepted=True, fee_disclosure_accepted=False
    )
    with pytest.raises(UnprocessableEntityException):
        await service.subscribe(user.id, dto)


@pytest.mark.asyncio
async def test_subscribe_rejects_when_series_paused():
    module = await _build_module()
    service = module.get(SubscriptionsService)
    _, series = await _seed_series(module, window=_OPEN_WINDOW)
    series_repo = module.get(repository_token(TokenSeries))
    await series_repo.update({"id": series.id}, {"paused": True})
    user, _ = await _seed_investor(module, email="i5@x.com", available_balance=50000)

    with pytest.raises(ConflictException):
        await service.subscribe(user.id, _subscribe_dto(series.id, 100))


@pytest.mark.asyncio
async def test_subscribe_rejects_outside_window():
    module = await _build_module()
    service = module.get(SubscriptionsService)
    _, series = await _seed_series(module, window=_CLOSED_WINDOW)
    user, _ = await _seed_investor(module, email="i6@x.com", available_balance=50000)

    with pytest.raises(ConflictException):
        await service.subscribe(user.id, _subscribe_dto(series.id, 100))


@pytest.mark.asyncio
async def test_cancel_pending_subscription_unlocks_funds():
    module = await _build_module()
    service = module.get(SubscriptionsService)
    _, series = await _seed_series(module, window=_OPEN_WINDOW)
    user, _ = await _seed_investor(module, email="i7@x.com", available_balance=50000)

    sub = await service.subscribe(user.id, _subscribe_dto(series.id, 100))
    cancelled = await service.cancel_my_subscription(user.id, sub.id)
    assert cancelled.status == "CANCELLED"

    accounts = module.get(repository_token(LedgerAccount))
    account = (await accounts.find())[0]
    assert float(account.available_balance) == 50000
    assert float(account.locked_balance) == 0

    # A cancelled subscription cannot be cancelled again -- illegal transition.
    with pytest.raises(ConflictException):
        await service.cancel_my_subscription(user.id, sub.id)


@pytest.mark.asyncio
async def test_mark_confirmed_before_funded_is_an_invalid_transition():
    module = await _build_module()
    service = module.get(SubscriptionsService)
    _, series = await _seed_series(module, window=_OPEN_WINDOW)
    user, _ = await _seed_investor(module, email="i8@x.com", available_balance=50000)

    sub = await service.subscribe(user.id, _subscribe_dto(series.id, 100))
    with pytest.raises(ConflictException):
        await service.mark_confirmed(officer_id=99, subscription_id=sub.id)


@pytest.mark.asyncio
async def test_allocate_rejects_while_window_still_open():
    module = await _build_module()
    service = module.get(SubscriptionsService)
    _, series = await _seed_series(module, window=_OPEN_WINDOW)

    with pytest.raises(ConflictException):
        await service.allocate(officer_id=99, series_id=series.id)


@pytest.mark.asyncio
async def test_allocate_full_allocation_creates_holding_and_settles_ledger():
    module = await _build_module()
    service = module.get(SubscriptionsService)
    proposal, series = await _seed_series(module, window=_OPEN_WINDOW, total_units=1000, unit_price=100)
    user, _ = await _seed_investor(module, email="i9@x.com", available_balance=50000)

    sub = await service.subscribe(user.id, _subscribe_dto(series.id, 100))
    await service.mark_funded(99, sub.id)
    await service.mark_confirmed(99, sub.id)
    await _close_window(module, proposal.id)

    result = await service.allocate(officer_id=99, series_id=series.id)
    assert result.pro_rata_ratio == 1.0
    assert result.allocated_subscription_count == 1

    updated = await service.get_my_subscription(user.id, sub.id)
    assert updated.status == "ALLOCATED"
    assert updated.allocated_units == 100

    holdings = module.get(repository_token(TokenHolding))
    holding = (await holdings.find())[0]
    assert float(holding.quantity) == 100
    assert float(holding.avg_cost_usd) == 100

    accounts = module.get(repository_token(LedgerAccount))
    account = (await accounts.find())[0]
    assert float(account.locked_balance) == 0
    assert float(account.available_balance) == 40000  # 50000 - 10000 locked, none unlocked (fully allocated)

    entries = module.get(repository_token(LedgerEntry))
    settlement = [e for e in await entries.find() if e.entry_type == "DEBIT_SUBSCRIPTION_SETTLEMENT"]
    assert len(settlement) == 1
    assert float(settlement[0].amount) == 10000


@pytest.mark.asyncio
async def test_allocate_pro_rata_oversubscription_unlocks_excess():
    module = await _build_module()
    service = module.get(SubscriptionsService)
    # Only 100 units of supply, two investors each request 100 -> 50% pro-rata each.
    proposal, series = await _seed_series(module, window=_OPEN_WINDOW, total_units=100, unit_price=100, min_units=1)
    user_a, _ = await _seed_investor(module, email="a@x.com", available_balance=50000)
    user_b, _ = await _seed_investor(module, email="b@x.com", available_balance=50000)

    sub_a = await service.subscribe(user_a.id, _subscribe_dto(series.id, 100))
    sub_b = await service.subscribe(user_b.id, _subscribe_dto(series.id, 100))
    for sub in (sub_a, sub_b):
        await service.mark_funded(99, sub.id)
        await service.mark_confirmed(99, sub.id)
    await _close_window(module, proposal.id)

    result = await service.allocate(officer_id=99, series_id=series.id)
    assert result.pro_rata_ratio == 0.5
    assert result.allocated_subscription_count == 2

    updated_a = await service.get_my_subscription(user_a.id, sub_a.id)
    assert updated_a.allocated_units == 50

    accounts = module.get(repository_token(LedgerAccount))
    for account in await accounts.find():
        # Locked 10000, half (5000) settled, half (5000) unlocked back to available.
        assert float(account.locked_balance) == 0
        assert float(account.available_balance) == 45000


@pytest.mark.asyncio
async def test_allocate_is_a_no_op_when_nothing_is_confirmed():
    module = await _build_module()
    service = module.get(SubscriptionsService)
    _, series = await _seed_series(module, window=_CLOSED_WINDOW)

    result = await service.allocate(officer_id=99, series_id=series.id)
    assert result.allocated_subscription_count == 0
    assert result.pro_rata_ratio is None


@pytest.mark.asyncio
async def test_marketplace_lists_only_open_launched_series():
    module = await _build_module()
    service = module.get(SubscriptionsService)
    await _seed_series(module, window=_OPEN_WINDOW)
    await _seed_series(module, window=_CLOSED_WINDOW)

    listing = await service.list_marketplace(skip=0, take=50)
    assert listing.total == 1
