from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from austial import ConflictException, Injectable, NotFoundException, UnprocessableEntityException
from austial.config import ConfigService
from austial.orm import DataSource, FindOptions, InjectRepository, Repository

from src.i18n.i18n import t
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.ledger.entities.funding_instruction import FundingInstruction
from src.modules.ledger.entities.ledger_account import LedgerAccount
from src.modules.ledger.entities.ledger_entry import LedgerEntry
from src.modules.ledger.entities.payout_instruction import PayoutInstruction
from src.modules.ledger.ledger_dto import (
    ConfirmFundingInstructionDto,
    FundingInstructionListDto,
    FundingInstructionResponseDto,
    LedgerAccountResponseDto,
    LedgerEntryListDto,
    LedgerEntryResponseDto,
    PayoutInstructionResponseDto,
    RecordPayoutInstructionDto,
    RequestFundingInstructionDto,
)

# How long a `PENDING` funding instruction stays valid before it *would* be eligible for expiry --
# stored on `expires_at`, but nothing automatically transitions it to `EXPIRED` yet (see
# `FundingInstruction`'s docstring -- that's a future Celery-task follow-up).
_FUNDING_INSTRUCTION_VALIDITY_DAYS = 7


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_account_dto(account: LedgerAccount) -> LedgerAccountResponseDto:
    return LedgerAccountResponseDto(
        id=account.id,
        currency=account.currency,
        available_balance=float(account.available_balance),
        locked_balance=float(account.locked_balance),
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def _to_entry_dto(entry: LedgerEntry) -> LedgerEntryResponseDto:
    return LedgerEntryResponseDto(
        id=entry.id,
        entry_type=entry.entry_type,
        amount=float(entry.amount),
        currency=entry.currency,
        balance_after=float(entry.balance_after),
        reference_type=entry.reference_type,
        reference_id=entry.reference_id,
        created_at=entry.created_at,
    )


def _to_payout_dto(payout: PayoutInstruction) -> PayoutInstructionResponseDto:
    return PayoutInstructionResponseDto(
        id=payout.id,
        investor_id=payout.investor.id,
        amount=float(payout.amount),
        currency=payout.currency,
        status=payout.status,
        memo=payout.memo,
        recorded_by_user_id=payout.recorded_by_user_id,
        recorded_at=payout.recorded_at,
        created_at=payout.created_at,
    )


@Injectable()
class LedgerService:
    def __init__(
        self,
        config: ConfigService,
        data_source: DataSource,
        investor_profiles: Repository[InvestorProfile] = InjectRepository(InvestorProfile),
        ledger_accounts: Repository[LedgerAccount] = InjectRepository(LedgerAccount),
        ledger_entries: Repository[LedgerEntry] = InjectRepository(LedgerEntry),
        funding_instructions: Repository[FundingInstruction] = InjectRepository(FundingInstruction),
        payout_instructions: Repository[PayoutInstruction] = InjectRepository(PayoutInstruction),
    ):
        self.ds = data_source
        self.investor_profiles = investor_profiles
        self.ledger_accounts = ledger_accounts
        self.ledger_entries = ledger_entries
        self.funding_instructions = funding_instructions
        self.payout_instructions = payout_instructions

        # Static beneficiary/wire display details -- config-driven (not hardcoded, not entity
        # columns, see `FundingInstruction`'s docstring for why) since they're the same for every
        # instruction and never change per-request, only differ per deployment environment.
        self._beneficiary_name = config.get_or_throw("LEDGER_BENEFICIARY_NAME")
        self._beneficiary_bank_name = config.get_or_throw("LEDGER_BENEFICIARY_BANK_NAME")
        self._beneficiary_account_number = config.get_or_throw("LEDGER_BENEFICIARY_ACCOUNT_NUMBER")
        self._beneficiary_swift_bic = config.get_or_throw("LEDGER_BENEFICIARY_SWIFT_BIC")

    # -- investor-facing: account + funding ----------------------------------------------------

    async def get_my_account(self, user_id: int) -> LedgerAccountResponseDto:
        investor = await self._get_investor_by_user_or_raise(user_id)
        account = await self._get_or_create_account(investor)
        return _to_account_dto(account)

    async def list_my_entries(self, user_id: int, *, skip: int, take: int) -> LedgerEntryListDto:
        investor = await self._get_investor_by_user_or_raise(user_id)
        account = await self._get_or_create_account(investor)
        entries, total = await (
            self.ledger_entries.create_query_builder("e")
            .where("e.account_id = :account_id", {"account_id": account.id})
            .add_order_by("e.id", "DESC")
            .skip(skip)
            .take(take)
            .get_many_and_count()
        )
        return LedgerEntryListDto(total=total, items=[_to_entry_dto(e) for e in entries])

    async def request_funding_instruction(
        self, user_id: int, dto: RequestFundingInstructionDto
    ) -> FundingInstructionResponseDto:
        """Investor-initiated: records a ``PENDING`` ``FundingInstruction`` and returns it
        alongside the static wire/beneficiary details -- no money moves here, this is purely
        "here's what to wire and what reference code to put on it" (see this module's and
        ``FundingInstruction``'s docstrings for why)."""
        investor = await self._get_investor_by_user_or_raise(user_id)
        reference_code = f"FUND-{uuid.uuid4().hex[:12].upper()}"
        now = _now()
        instruction = await self.funding_instructions.save(
            FundingInstruction(  # type: ignore[call-arg]
                investor=investor,
                reference_code=reference_code,
                amount=dto.amount,
                currency=dto.currency,
                status="PENDING",
                expires_at=now + timedelta(days=_FUNDING_INSTRUCTION_VALIDITY_DAYS),
            )
        )
        return self._to_funding_dto(instruction)

    async def get_my_funding_instruction(self, user_id: int, instruction_id: int) -> FundingInstructionResponseDto:
        investor = await self._get_investor_by_user_or_raise(user_id)
        instruction = await self._get_funding_instruction_or_raise(instruction_id)
        if instruction.investor.id != investor.id:
            raise NotFoundException(t("ledger.error.funding_instruction_not_found"))
        return self._to_funding_dto(instruction)

    # -- compliance-officer/admin-facing: confirmation + payouts -------------------------------

    async def list_funding_instructions(self, *, status: str | None, skip: int, take: int) -> FundingInstructionListDto:
        query = self.funding_instructions.create_query_builder("f").left_join_and_select("f.investor", "investor")
        if status:
            # `CAST(... AS TEXT)` -- see `kyc_service.py`'s equivalent workaround: austial.orm's
            # QueryBuilder doesn't cast bound params to a column's native Postgres enum type, so
            # a plain `f.status = :status` raises `UndefinedFunctionError` (enum = varchar) on
            # real Postgres (SQLite in tests has no native enum type, so this doesn't surface
            # there). Framework gap flagged to austial-framework-dev, not fixed at that layer here.
            query = query.where("CAST(f.status AS TEXT) = :status", {"status": status})
        instructions, total = await query.add_order_by("f.id", "ASC").skip(skip).take(take).get_many_and_count()
        return FundingInstructionListDto(total=total, items=[self._to_funding_dto(i) for i in instructions])

    async def confirm_funding_instruction(
        self, officer_id: int, instruction_id: int, dto: ConfirmFundingInstructionDto
    ) -> FundingInstructionResponseDto:
        """The credit path. See this module's and ``LedgerEntry``'s docstrings for the
        idempotency contract -- ``idempotency_key`` defaults to a value deterministic in
        ``instruction_id`` alone, so re-confirming the same instruction (double-click, or a retry
        that omits an explicit key) always collides on the same key rather than silently minting
        a fresh one that would pass the pre-check and double-credit the account."""
        instruction = await self._get_funding_instruction_or_raise(instruction_id)
        if instruction.status != "PENDING":
            raise ConflictException(t("ledger.error.funding_instruction_not_pending"))

        idempotency_key = dto.idempotency_key or f"funding:{instruction.id}:confirm"
        already_processed = await self.ledger_entries.find_one_by({"idempotency_key": idempotency_key})
        if already_processed is not None:
            raise ConflictException(t("ledger.error.idempotency_key_already_used"))

        investor = instruction.investor
        account = await self._get_or_create_account(investor)
        now = _now()

        async def work(em: Any) -> LedgerEntry:
            fresh_account = await em.find_one(LedgerAccount, FindOptions(where={"id": account.id}))
            new_balance = float(fresh_account.available_balance) + float(instruction.amount)
            await em.update(LedgerAccount, fresh_account.id, {"available_balance": new_balance})
            entry = await em.save(
                LedgerEntry(  # type: ignore[call-arg]
                    account=fresh_account,
                    entry_type="CREDIT_FUNDING",
                    amount=instruction.amount,
                    currency=instruction.currency,
                    balance_after=new_balance,
                    reference_type="FUNDING_INSTRUCTION",
                    reference_id=instruction.id,
                    idempotency_key=idempotency_key,
                )
            )
            await em.update(
                FundingInstruction,
                instruction.id,
                {"status": "CONFIRMED", "confirmed_by_user_id": officer_id, "confirmed_at": now},
            )
            return entry

        await self.ds.transaction(work)
        instruction.status = "CONFIRMED"
        instruction.confirmed_by_user_id = officer_id
        instruction.confirmed_at = now
        return self._to_funding_dto(instruction)

    async def record_payout_instruction(
        self, officer_id: int, dto: RecordPayoutInstructionDto
    ) -> PayoutInstructionResponseDto:
        """The debit path. ``idempotency_key`` is mandatory here (unlike funding's optional key)
        because there is no prior ``PENDING`` row for the service to derive a deterministic
        default from -- see ``RecordPayoutInstructionDto``'s docstring."""
        investor = await self._get_investor_or_raise(dto.investor_id)

        already_processed = await self.ledger_entries.find_one_by({"idempotency_key": dto.idempotency_key})
        if already_processed is not None:
            raise ConflictException(t("ledger.error.idempotency_key_already_used"))

        account = await self._get_or_create_account(investor)
        if float(account.available_balance) < dto.amount:
            raise UnprocessableEntityException(t("ledger.error.insufficient_available_balance"))
        now = _now()

        async def work(em: Any) -> tuple[PayoutInstruction, LedgerEntry]:
            fresh_account = await em.find_one(LedgerAccount, FindOptions(where={"id": account.id}))
            if float(fresh_account.available_balance) < dto.amount:
                raise UnprocessableEntityException(t("ledger.error.insufficient_available_balance"))
            new_balance = float(fresh_account.available_balance) - dto.amount
            await em.update(LedgerAccount, fresh_account.id, {"available_balance": new_balance})
            payout = await em.save(
                PayoutInstruction(  # type: ignore[call-arg]
                    investor=investor,
                    amount=dto.amount,
                    currency=dto.currency,
                    status="RECORDED",
                    memo=dto.memo,
                    recorded_by_user_id=officer_id,
                    recorded_at=now,
                )
            )
            entry = await em.save(
                LedgerEntry(  # type: ignore[call-arg]
                    account=fresh_account,
                    entry_type="DEBIT_PAYOUT",
                    amount=dto.amount,
                    currency=dto.currency,
                    balance_after=new_balance,
                    reference_type="PAYOUT_INSTRUCTION",
                    reference_id=payout.id,
                    idempotency_key=dto.idempotency_key,
                )
            )
            return payout, entry

        payout, _entry = await self.ds.transaction(work)
        payout.investor = investor  # `em.save()` returns the instance as constructed -- already set, kept explicit.
        return _to_payout_dto(payout)

    # -- lock / unlock / settle -- Phase 6, consumed by ``SubscriptionsService`` -----------------
    #
    # These three move money between an account's `available_balance`/`locked_balance` (lock,
    # unlock) or shrink `locked_balance` outright (settle) -- see each method's own docstring for
    # why only `settle_locked_funds` produces a `LedgerEntry`. All three are called from inside a
    # caller-owned state-machine transition (`SubscriptionsService`'s `ALLOWED_TRANSITIONS`
    # already guarantees each subscription is locked/unlocked/settled at most once per legal path
    # through the state machine), so unlike `confirm_funding_instruction`/
    # `record_payout_instruction` there is no separate idempotency-key parameter here -- the
    # state machine *is* the idempotency guard.

    async def get_or_create_account(self, investor: InvestorProfile) -> LedgerAccount:
        """Public entry point onto ``_get_or_create_account`` for callers outside this module
        (``SubscriptionsService``) that need the raw ``LedgerAccount`` entity -- not its response
        DTO -- to pass into ``lock_within``/``unlock_within``/``settle_within`` below."""
        return await self._get_or_create_account(investor)

    async def lock_within(self, em: Any, account: LedgerAccount, amount: float) -> LedgerAccount:
        """``available_balance -> locked_balance``, against a caller-supplied ``EntityManager``
        (``em``) inside an *already-open* ``DataSource.transaction(...)`` block -- for callers
        (``SubscriptionsService.subscribe``) that need the lock to commit atomically together with
        other writes (the ``Subscription`` row itself) in a single transaction, rather than in the
        lock's own standalone one. ``lock_funds`` below is the self-transacting wrapper around this
        for callers that only need to lock in isolation. Fresh-re-reads the account by id (mirrors
        ``record_payout_instruction``'s check-then-fresh-re-check pattern) so a concurrent
        lock/unlock/settle on the same account can't race past the balance check. Raises
        ``UnprocessableEntityException`` if ``available_balance`` is insufficient -- checked
        *before* any write, so a caller's whole transaction (including e.g. the ``Subscription``
        row) rolls back cleanly rather than partially applying -- exactly this phase's task brief
        ("a subscription with insufficient available_balance must be rejected before any lock is
        attempted").

        **No ``LedgerEntry`` is written for this operation** -- deliberate. ``LedgerEntry``'s
        columns (in particular ``balance_after``) exist to give an account a chronological,
        auditable history of *total-balance-affecting* events (funding in, payout out). Locking
        does not change the account's total balance (``available + locked`` is invariant across
        this call) -- it only reclassifies part of that same total as "committed", so there is no
        total-balance-affecting event here to record. The generic ``AuditInterceptor`` still
        writes an ``AuditLog`` row for the HTTP request that triggered this (subscribing), and
        ``SubscriptionsService`` writes its own domain-level ``AuditLog`` entry alongside every
        subscription state transition -- see that module's docstring -- so the lock is not
        un-audited, it just isn't modelled as a ledger *entry*.
        """
        fresh = await em.find_one(LedgerAccount, FindOptions(where={"id": account.id}))
        if float(fresh.available_balance) < amount:
            raise UnprocessableEntityException(t("ledger.error.insufficient_available_balance"))
        new_available = float(fresh.available_balance) - amount
        new_locked = float(fresh.locked_balance) + amount
        await em.update(LedgerAccount, fresh.id, {"available_balance": new_available, "locked_balance": new_locked})
        return fresh

    async def unlock_within(self, em: Any, account: LedgerAccount, amount: float) -> LedgerAccount:
        """The exact reverse of ``lock_within`` -- ``locked_balance -> available_balance``, same
        caller-supplied-``em``/already-open-transaction contract. Used both by
        ``SubscriptionsService``'s ``CANCELLED``/``REFUNDED`` transitions (return *everything*
        that was locked) and by the allocation engine's pro-rata path (return only the
        *unallocated excess* of what was locked -- see ``SubscriptionsService.allocate``). Same
        no-``LedgerEntry`` reasoning as ``lock_within`` -- total balance is unchanged.
        """
        fresh = await em.find_one(LedgerAccount, FindOptions(where={"id": account.id}))
        if float(fresh.locked_balance) < amount:
            raise ConflictException(t("ledger.error.insufficient_locked_balance"))
        new_available = float(fresh.available_balance) + amount
        new_locked = float(fresh.locked_balance) - amount
        await em.update(LedgerAccount, fresh.id, {"available_balance": new_available, "locked_balance": new_locked})
        return fresh

    async def settle_within(self, em: Any, account: LedgerAccount, amount: float, *, reference_id: int) -> LedgerEntry:
        """Consumes ``locked_balance`` outright, same caller-supplied-``em`` contract -- called
        once a subscription's locked funds are actually spent on an allocated ``TokenHolding``
        (``SubscriptionsService.allocate``). Unlike lock/unlock, this **does** shrink the account's
        total balance (funds have left the investor's ledger account, paid for the asset), so it
        **does** write a ``LedgerEntry`` -- ``entry_type="DEBIT_SUBSCRIPTION_SETTLEMENT"``,
        ``reference_type="SUBSCRIPTION"`` -- to stay consistent with Phase 5's "every
        balance-affecting event gets an entry" rule. See ``LedgerEntry.LEDGER_ENTRY_TYPES``'s
        docstring for why ``balance_after`` here is ``locked_balance`` after the debit rather than
        ``available_balance`` (which this call never touches). ``idempotency_key`` is deterministic
        in ``reference_id`` (the ``Subscription.id``) alone -- a subscription is only ever settled
        once, at the single ``CONFIRMED -> ALLOCATED`` transition its own state machine allows.
        """
        fresh = await em.find_one(LedgerAccount, FindOptions(where={"id": account.id}))
        if float(fresh.locked_balance) < amount:
            raise ConflictException(t("ledger.error.insufficient_locked_balance"))
        new_locked = float(fresh.locked_balance) - amount
        await em.update(LedgerAccount, fresh.id, {"locked_balance": new_locked})
        return await em.save(
            LedgerEntry(  # type: ignore[call-arg]
                account=fresh,
                entry_type="DEBIT_SUBSCRIPTION_SETTLEMENT",
                amount=amount,
                currency=fresh.currency,
                balance_after=new_locked,
                reference_type="SUBSCRIPTION",
                reference_id=reference_id,
                idempotency_key=f"subscription:{reference_id}:settle",
            )
        )

    async def lock_funds(self, investor: InvestorProfile, amount: float) -> LedgerAccount:
        """Standalone, self-transacting wrapper around ``lock_within`` for callers that only need
        to lock in isolation (not used by ``SubscriptionsService``, which needs the lock atomic
        together with its own ``Subscription`` row write -- see ``lock_within``'s docstring --
        kept here for API completeness/direct unit-testability of the lock primitive alone)."""
        account = await self._get_or_create_account(investor)

        async def work(em: Any) -> LedgerAccount:
            return await self.lock_within(em, account, amount)

        await self.ds.transaction(work)
        return await self._get_or_create_account(investor)

    async def unlock_funds(self, investor: InvestorProfile, amount: float) -> LedgerAccount:
        """Standalone, self-transacting wrapper around ``unlock_within`` -- see ``lock_funds``'s
        docstring for why ``SubscriptionsService`` uses ``unlock_within`` directly instead."""
        account = await self._get_or_create_account(investor)

        async def work(em: Any) -> LedgerAccount:
            return await self.unlock_within(em, account, amount)

        await self.ds.transaction(work)
        return await self._get_or_create_account(investor)

    # -- internals ------------------------------------------------------------------------------

    async def _get_or_create_account(self, investor: InvestorProfile) -> LedgerAccount:
        # `find_one_by` only resolves *mapped attribute* names (plain columns), not relation FK
        # columns -- see `investors_service._find_profile`'s identical raw-SQL-on-the-FK-column
        # convention for the same reason -- so this goes through the query builder instead.
        account = await (
            self.ledger_accounts.create_query_builder("account")
            .where("account.investor_id = :investor_id", {"investor_id": investor.id})
            .get_one()
        )
        if account is not None:
            return account
        return await self.ledger_accounts.save(
            LedgerAccount(investor=investor, currency="USD", available_balance=0, locked_balance=0)  # type: ignore[call-arg]
        )

    async def _get_investor_by_user_or_raise(self, user_id: int) -> InvestorProfile:
        investor = await (
            self.investor_profiles.create_query_builder("investor")
            .where("investor.user_id = :user_id", {"user_id": user_id})
            .get_one()
        )
        if investor is None:
            raise NotFoundException(t("ledger.error.investor_profile_required"))
        return investor

    async def _get_investor_or_raise(self, investor_id: int) -> InvestorProfile:
        investor = await self.investor_profiles.find_one_by({"id": investor_id})
        if investor is None:
            raise NotFoundException(t("ledger.error.investor_not_found"))
        return investor

    async def _get_funding_instruction_or_raise(self, instruction_id: int) -> FundingInstruction:
        instruction = await self.funding_instructions.find_one(
            FindOptions(where={"id": instruction_id}, relations=["investor"])
        )
        if instruction is None:
            raise NotFoundException(t("ledger.error.funding_instruction_not_found"))
        return instruction

    def _to_funding_dto(self, instruction: FundingInstruction) -> FundingInstructionResponseDto:
        return FundingInstructionResponseDto(
            id=instruction.id,
            reference_code=instruction.reference_code,
            amount=float(instruction.amount),
            currency=instruction.currency,
            status=instruction.status,
            expires_at=instruction.expires_at,
            confirmed_at=instruction.confirmed_at,
            created_at=instruction.created_at,
            beneficiary_name=self._beneficiary_name,
            beneficiary_bank_name=self._beneficiary_bank_name,
            beneficiary_account_number=self._beneficiary_account_number,
            beneficiary_swift_bic=self._beneficiary_swift_bic,
        )
