from __future__ import annotations

import pytest
from austial import ConflictException, NotFoundException, UnprocessableEntityException
from austial.config import ConfigService
from austial.orm import AppendOnlyViolationError, DataSource, OrmModule, repository_token
from austial.testing import Test
from pydantic import ValidationError

from src.modules.auth.entities.user import User
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.investors.entities.wallet_mapping import WalletMapping
from src.modules.investors.investors_dto import CreateInvestorProfileDto
from src.modules.investors.investors_service import InvestorsService
from src.modules.ledger.entities.funding_instruction import FundingInstruction
from src.modules.ledger.entities.ledger_account import LedgerAccount
from src.modules.ledger.entities.ledger_entry import LedgerEntry
from src.modules.ledger.entities.payout_instruction import PayoutInstruction
from src.modules.ledger.ledger_dto import (
    ConfirmFundingInstructionDto,
    RecordPayoutInstructionDto,
    RequestFundingInstructionDto,
)
from src.modules.ledger.ledger_service import LedgerService

_PROFILE_DTO = CreateInvestorProfileDto(investor_type="INDIVIDUAL", jurisdiction="in", risk_profile="MODERATE")


def _config_service() -> ConfigService:
    return ConfigService(
        {
            "LEDGER_BENEFICIARY_NAME": "Austial GIFT City IBU Client Settlement Account",
            "LEDGER_BENEFICIARY_BANK_NAME": "Test Bank",
            "LEDGER_BENEFICIARY_ACCOUNT_NUMBER": "000123456789",
            "LEDGER_BENEFICIARY_SWIFT_BIC": "TESTINBBXXX",
        }
    )


async def _build_module():
    module = await Test.create_testing_module(
        imports=[
            OrmModule.for_root(
                type_="sqlite",
                url="sqlite+aiosqlite:///:memory:",
                entities=[
                    User,
                    InvestorProfile,
                    WalletMapping,
                    LedgerAccount,
                    LedgerEntry,
                    FundingInstruction,
                    PayoutInstruction,
                ],
                synchronize=True,
            ),
            OrmModule.for_feature(
                [
                    User,
                    InvestorProfile,
                    WalletMapping,
                    LedgerAccount,
                    LedgerEntry,
                    FundingInstruction,
                    PayoutInstruction,
                ]
            ),
        ],
        providers=[
            LedgerService,
            InvestorsService,
            {"provide": ConfigService, "useValue": _config_service()},
        ],
    ).compile()
    await module.get(DataSource).initialize()
    return module


async def _seed_investor(module, *, email: str = "investor@example.com"):
    users = module.get(repository_token(User))
    user = await users.save(User(email=email, password_hash="hashed", role="INVESTOR"))  # type: ignore[call-arg]
    investors_service = module.get(InvestorsService)
    await investors_service.create_profile(user.id, _PROFILE_DTO)
    return user


@pytest.mark.asyncio
async def test_get_my_account_lazily_creates_a_zero_balance_account():
    module = await _build_module()
    user = await _seed_investor(module)
    service = module.get(LedgerService)

    account = await service.get_my_account(user.id)

    assert account.available_balance == 0
    assert account.locked_balance == 0
    assert account.currency == "USD"


@pytest.mark.asyncio
async def test_request_funding_instruction_returns_wire_details_and_reference_code():
    module = await _build_module()
    user = await _seed_investor(module)
    service = module.get(LedgerService)

    instruction = await service.request_funding_instruction(
        user.id, RequestFundingInstructionDto(amount=1000, currency="USD")
    )

    assert instruction.status == "PENDING"
    assert instruction.reference_code.startswith("FUND-")
    assert instruction.beneficiary_bank_name == "Test Bank"
    assert instruction.beneficiary_swift_bic == "TESTINBBXXX"


def test_request_funding_instruction_rejects_inr():
    with pytest.raises(ValidationError):
        RequestFundingInstructionDto(amount=1000, currency="INR")


@pytest.mark.asyncio
async def test_confirm_funding_instruction_credits_the_account_and_writes_a_ledger_entry():
    module = await _build_module()
    user = await _seed_investor(module)
    service = module.get(LedgerService)
    instruction = await service.request_funding_instruction(
        user.id, RequestFundingInstructionDto(amount=1500, currency="USD")
    )

    confirmed = await service.confirm_funding_instruction(
        officer_id=1, instruction_id=instruction.id, dto=ConfirmFundingInstructionDto()
    )

    assert confirmed.status == "CONFIRMED"
    account = await service.get_my_account(user.id)
    assert account.available_balance == 1500

    entries = await service.list_my_entries(user.id, skip=0, take=10)
    assert entries.total == 1
    assert entries.items[0].entry_type == "CREDIT_FUNDING"
    assert entries.items[0].balance_after == 1500


@pytest.mark.asyncio
async def test_confirm_funding_instruction_is_idempotent_against_a_repeat_confirm():
    """★ Idempotency -- see the build plan's "mandatory on every credit path" instruction and
    ``LedgerService``'s docstring. A second confirm attempt on an already-``CONFIRMED``
    instruction must not double-credit the account."""
    module = await _build_module()
    user = await _seed_investor(module)
    service = module.get(LedgerService)
    instruction = await service.request_funding_instruction(
        user.id, RequestFundingInstructionDto(amount=500, currency="USD")
    )
    await service.confirm_funding_instruction(
        officer_id=1, instruction_id=instruction.id, dto=ConfirmFundingInstructionDto()
    )

    with pytest.raises(ConflictException):
        await service.confirm_funding_instruction(
            officer_id=1, instruction_id=instruction.id, dto=ConfirmFundingInstructionDto()
        )

    account = await service.get_my_account(user.id)
    assert account.available_balance == 500  # unchanged -- not double-credited

    entries_repo = module.get(repository_token(LedgerEntry))
    assert await entries_repo.count() == 1


@pytest.mark.asyncio
async def test_confirm_funding_instruction_rejects_reusing_an_explicit_idempotency_key():
    """Same idempotency guarantee, but exercised via a caller-supplied key (the webhook-ready
    seam) rather than the deterministic default -- a retry with the *same* explicit key on a
    *different* (still-PENDING) instruction must still be refused."""
    module = await _build_module()
    user = await _seed_investor(module)
    service = module.get(LedgerService)
    instruction_a = await service.request_funding_instruction(
        user.id, RequestFundingInstructionDto(amount=200, currency="USD")
    )
    instruction_b = await service.request_funding_instruction(
        user.id, RequestFundingInstructionDto(amount=300, currency="USD")
    )
    shared_key = "bank-webhook-event-001"
    await service.confirm_funding_instruction(
        officer_id=1, instruction_id=instruction_a.id, dto=ConfirmFundingInstructionDto(idempotency_key=shared_key)
    )

    with pytest.raises(ConflictException):
        await service.confirm_funding_instruction(
            officer_id=1,
            instruction_id=instruction_b.id,
            dto=ConfirmFundingInstructionDto(idempotency_key=shared_key),
        )


@pytest.mark.asyncio
async def test_confirm_funding_instruction_rejects_a_non_pending_instruction():
    module = await _build_module()
    user = await _seed_investor(module)
    service = module.get(LedgerService)
    instruction = await service.request_funding_instruction(
        user.id, RequestFundingInstructionDto(amount=100, currency="USD")
    )
    await service.confirm_funding_instruction(
        officer_id=1, instruction_id=instruction.id, dto=ConfirmFundingInstructionDto()
    )

    with pytest.raises(ConflictException):
        await service.confirm_funding_instruction(
            officer_id=1, instruction_id=instruction.id, dto=ConfirmFundingInstructionDto(idempotency_key="another-key")
        )


@pytest.mark.asyncio
async def test_record_payout_instruction_debits_the_account_and_writes_a_ledger_entry():
    module = await _build_module()
    user = await _seed_investor(module)
    service = module.get(LedgerService)
    instruction = await service.request_funding_instruction(
        user.id, RequestFundingInstructionDto(amount=1000, currency="USD")
    )
    await service.confirm_funding_instruction(
        officer_id=1, instruction_id=instruction.id, dto=ConfirmFundingInstructionDto()
    )
    investors = module.get(repository_token(InvestorProfile))
    investor = (await investors.find())[0]

    payout = await service.record_payout_instruction(
        officer_id=2,
        dto=RecordPayoutInstructionDto(
            investor_id=investor.id, amount=400, currency="USD", memo="Redemption payout", idempotency_key="payout-001"
        ),
    )

    assert payout.status == "RECORDED"
    account = await service.get_my_account(user.id)
    assert account.available_balance == 600

    entries = await service.list_my_entries(user.id, skip=0, take=10)
    assert entries.total == 2
    assert entries.items[0].entry_type == "DEBIT_PAYOUT"  # most recent first
    assert entries.items[0].balance_after == 600


@pytest.mark.asyncio
async def test_record_payout_instruction_rejects_insufficient_balance():
    module = await _build_module()
    user = await _seed_investor(module)
    service = module.get(LedgerService)
    await service.get_my_account(user.id)  # lazily create a zero-balance account
    investors = module.get(repository_token(InvestorProfile))
    investor = (await investors.find())[0]

    with pytest.raises(UnprocessableEntityException):
        await service.record_payout_instruction(
            officer_id=2,
            dto=RecordPayoutInstructionDto(
                investor_id=investor.id, amount=50, currency="USD", idempotency_key="payout-insufficient"
            ),
        )


@pytest.mark.asyncio
async def test_record_payout_instruction_reusing_idempotency_key_is_rejected():
    module = await _build_module()
    user = await _seed_investor(module)
    service = module.get(LedgerService)
    instruction = await service.request_funding_instruction(
        user.id, RequestFundingInstructionDto(amount=1000, currency="USD")
    )
    await service.confirm_funding_instruction(
        officer_id=1, instruction_id=instruction.id, dto=ConfirmFundingInstructionDto()
    )
    investors = module.get(repository_token(InvestorProfile))
    investor = (await investors.find())[0]
    dto = RecordPayoutInstructionDto(investor_id=investor.id, amount=100, currency="USD", idempotency_key="dup-key")
    await service.record_payout_instruction(officer_id=2, dto=dto)

    with pytest.raises(ConflictException):
        await service.record_payout_instruction(officer_id=2, dto=dto)


@pytest.mark.asyncio
async def test_ledger_entry_is_append_only():
    """★ Framework-level enforcement -- see ``LedgerEntry``'s docstring and ``AuditLog``'s
    identical convention. An UPDATE-shaped ``save()``/``Repository.update()`` against an already-
    persisted ``LedgerEntry`` must raise ``AppendOnlyViolationError``, INSERT must not."""
    module = await _build_module()
    user = await _seed_investor(module)
    service = module.get(LedgerService)
    instruction = await service.request_funding_instruction(
        user.id, RequestFundingInstructionDto(amount=100, currency="USD")
    )
    await service.confirm_funding_instruction(
        officer_id=1, instruction_id=instruction.id, dto=ConfirmFundingInstructionDto()
    )
    entries_repo = module.get(repository_token(LedgerEntry))
    entry = (await entries_repo.find())[0]

    with pytest.raises(AppendOnlyViolationError):
        await entries_repo.update({"id": entry.id}, {"amount": 999})

    with pytest.raises(AppendOnlyViolationError):
        await entries_repo.remove(entry)


@pytest.mark.asyncio
async def test_get_my_funding_instruction_rejects_access_to_another_investors_instruction():
    module = await _build_module()
    owner = await _seed_investor(module, email="owner@example.com")
    other = await _seed_investor(module, email="other@example.com")
    service = module.get(LedgerService)
    instruction = await service.request_funding_instruction(
        owner.id, RequestFundingInstructionDto(amount=100, currency="USD")
    )

    with pytest.raises(NotFoundException):
        await service.get_my_funding_instruction(other.id, instruction.id)
