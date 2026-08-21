from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal
from typing import Any

from austial import ConflictException, Injectable, NotFoundException, UnprocessableEntityException
from austial.orm import DataSource, FindOptions, InjectRepository, Repository

from src.i18n.i18n import t
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.holdings.entities.token_holding import TokenHolding
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.issuance.entities.token_series import TokenSeries
from src.modules.issuance.entities.tokenization_proposal import TokenizationProposal
from src.modules.ledger.ledger_service import LedgerService
from src.modules.subscriptions.entities.subscription import Subscription
from src.modules.subscriptions.subscriptions_dto import (
    AllocationResultDto,
    CreateSubscriptionDto,
    MarketplaceListDto,
    MarketplaceTokenSeriesDto,
    SubscriptionListDto,
    SubscriptionResponseDto,
)

# Legal status transitions -- see this module's docstring for the reasoning behind extending
# `REFUNDED` past what the build plan's ASCII diagram literally draws.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"FUNDED", "CANCELLED"},
    "FUNDED": {"CONFIRMED", "REFUNDED"},
    "CONFIRMED": {"ALLOCATED", "REFUNDED"},
    "ALLOCATED": set(),
    "REFUNDED": set(),
    "CANCELLED": set(),
}

_UNITS_QUANT = Decimal("0.00000001")  # Numeric(28, 8)
_USD_QUANT = Decimal("0.01")  # Numeric(18, 2)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_dto(subscription: Subscription) -> SubscriptionResponseDto:
    return SubscriptionResponseDto(
        id=subscription.id,
        investor_id=subscription.investor.id,
        token_series_id=subscription.token_series.id,
        symbol=subscription.token_series.symbol,
        units=float(subscription.units),
        amount_usd=float(subscription.amount_usd),
        allocated_units=float(subscription.allocated_units) if subscription.allocated_units is not None else None,
        status=subscription.status,
        risk_disclosure_accepted=subscription.risk_disclosure_accepted,
        fee_disclosure_accepted=subscription.fee_disclosure_accepted,
        disclosures_acknowledged_at=subscription.disclosures_acknowledged_at,
        processed_by_user_id=subscription.processed_by_user_id,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
    )


def _to_marketplace_dto(series: TokenSeries) -> MarketplaceTokenSeriesDto:
    proposal = series.proposal
    asset = proposal.asset
    return MarketplaceTokenSeriesDto(
        id=series.id,
        symbol=series.symbol,
        asset_id=asset.id,
        asset_name=asset.name,
        asset_class=asset.asset_class,
        issuer_id=proposal.issuer.id,
        total_supply=float(series.total_supply),
        unit_price_usd=float(proposal.unit_price_usd),
        min_subscription_units=float(proposal.min_subscription_units),
        subscription_start_at=proposal.subscription_start_at,
        subscription_end_at=proposal.subscription_end_at,
    )


@Injectable()
class SubscriptionsService:
    def __init__(
        self,
        data_source: DataSource,
        ledger_service: LedgerService,
        investor_profiles: Repository[InvestorProfile] = InjectRepository(InvestorProfile),
        token_series: Repository[TokenSeries] = InjectRepository(TokenSeries),
        proposals: Repository[TokenizationProposal] = InjectRepository(TokenizationProposal),
        subscriptions: Repository[Subscription] = InjectRepository(Subscription),
        holdings: Repository[TokenHolding] = InjectRepository(TokenHolding),
        audit_logs: Repository[AuditLog] = InjectRepository(AuditLog),
    ):
        self.ds = data_source
        self.ledger_service = ledger_service
        self.investor_profiles = investor_profiles
        self.token_series = token_series
        self.proposals = proposals
        self.subscriptions = subscriptions
        self.holdings = holdings
        self.audit_logs = audit_logs

    # -- marketplace (investor-facing, read-only) ----------------------------------------------

    async def list_marketplace(self, *, skip: int, take: int) -> MarketplaceListDto:
        """ "Launched and open for subscription" -- ``proposal.status == "LAUNCHED"``, the series
        isn't ``paused`` (circuit breaker), and ``now`` falls inside the proposal's subscription
        window. Filtered/paginated entirely in SQL (not a Python post-filter) so ``total`` stays
        accurate under pagination.

        ★ Two single-hop queries, not one three-way chained join: ``austial.orm``'s
        ``QueryBuilder.left_join_and_select`` only resolves a join's relation name against the
        *root* entity's metadata (confirmed in ``austial-py/packages/orm/src/austial/orm/driver/
        sqlalchemy_support.py::compile_select`` -- every join condition is compiled against
        ``root_table`` regardless of which alias the relation path nominally chains off), so a
        second-level join like ``"p.asset"`` off an already-joined (non-root) alias ``"p"`` raises
        ``RelationNotFoundError`` rather than joining through ``p``. This is a framework gap
        (flagged to ``austial-framework-dev``, not worked around at the framework layer here) --
        the fix at this call site is two single-hop queries merged in Python instead of one
        three-way chain."""
        now = _now()
        series_list, total = await (
            self.token_series.create_query_builder("s")
            .left_join_and_select("s.proposal", "p")
            .where("p.status = :status", {"status": "LAUNCHED"})
            .and_where("s.paused = :paused", {"paused": False})
            .and_where("p.subscription_start_at <= :now", {"now": now})
            .and_where("p.subscription_end_at >= :now", {"now": now})
            .add_order_by("s.id", "DESC")
            .skip(skip)
            .take(take)
            .get_many_and_count()
        )
        items = []
        for series in series_list:
            # Page size is small (default 50) -- one single-hop query per series to resolve its
            # proposal's asset/issuer, rather than an unsupported multi-value `IN (...)` merge.
            proposal = await (
                self.proposals.create_query_builder("p")
                .left_join_and_select("p.asset", "asset")
                .left_join_and_select("p.issuer", "issuer")
                .where("p.id = :id", {"id": series.proposal.id})
                .get_one()
            )
            series.proposal = proposal
            items.append(_to_marketplace_dto(series))
        return MarketplaceListDto(total=total, items=items)

    # -- investor-facing: subscribe / view / cancel ----------------------------------------------

    async def subscribe(self, user_id: int, dto: CreateSubscriptionDto) -> SubscriptionResponseDto:
        investor = await self._get_investor_by_user_or_raise(user_id)
        series = await self._get_series_with_proposal_or_raise(dto.token_series_id)

        if series.paused:
            raise ConflictException(t("subscriptions.error.token_series_paused"))
        now = _now()
        if not (series.proposal.subscription_start_at <= now <= series.proposal.subscription_end_at):
            raise ConflictException(t("subscriptions.error.subscription_window_closed"))
        if dto.units < float(series.proposal.min_subscription_units):
            raise UnprocessableEntityException(t("subscriptions.error.below_minimum_subscription"))
        if not (dto.risk_disclosure_accepted and dto.fee_disclosure_accepted):
            raise UnprocessableEntityException(t("subscriptions.error.disclosures_not_accepted"))

        amount_usd = float(
            (Decimal(str(dto.units)) * Decimal(str(series.proposal.unit_price_usd))).quantize(
                _USD_QUANT, rounding=ROUND_DOWN
            )
        )
        account = await self.ledger_service.get_or_create_account(investor)
        acknowledged_at = now

        async def work(em: Any) -> Subscription:
            # ★ Atomic: the lock and the `Subscription` row land together or neither does -- see
            # this module's docstring on why `lock_within` (not `lock_funds`) is used here.
            await self.ledger_service.lock_within(em, account, amount_usd)
            return await em.save(
                Subscription(  # type: ignore[call-arg]
                    investor=investor,
                    token_series=series,
                    units=dto.units,
                    amount_usd=amount_usd,
                    status="PENDING",
                    risk_disclosure_accepted=dto.risk_disclosure_accepted,
                    fee_disclosure_accepted=dto.fee_disclosure_accepted,
                    disclosures_acknowledged_at=acknowledged_at,
                )
            )

        subscription = await self.ds.transaction(work)
        subscription.investor = investor
        subscription.token_series = series

        await self._write_audit_log(
            entity_id=str(subscription.id),
            actor_user_id=user_id,
            action="subscriptions.subscription.created",
            before_state=None,
            after_state={"status": "PENDING", "units": dto.units, "amount_usd": amount_usd},
        )
        return _to_dto(subscription)

    async def list_my_subscriptions(self, user_id: int, *, skip: int, take: int) -> SubscriptionListDto:
        investor = await self._get_investor_by_user_or_raise(user_id)
        subs, total = await (
            self.subscriptions.create_query_builder("sub")
            .left_join_and_select("sub.token_series", "series")
            .left_join_and_select("sub.investor", "investor")
            .where("sub.investor_id = :investor_id", {"investor_id": investor.id})
            .add_order_by("sub.id", "DESC")
            .skip(skip)
            .take(take)
            .get_many_and_count()
        )
        return SubscriptionListDto(total=total, items=[_to_dto(s) for s in subs])

    async def get_my_subscription(self, user_id: int, subscription_id: int) -> SubscriptionResponseDto:
        investor = await self._get_investor_by_user_or_raise(user_id)
        subscription = await self._get_own_subscription_or_raise(subscription_id, investor.id)
        return _to_dto(subscription)

    async def cancel_my_subscription(self, user_id: int, subscription_id: int) -> SubscriptionResponseDto:
        """Investor self-service -- ``PENDING`` only, per ``ALLOWED_TRANSITIONS``. Unlocks the
        full locked amount back to ``available_balance``, atomically with the status flip."""
        investor = await self._get_investor_by_user_or_raise(user_id)
        subscription = await self._get_own_subscription_or_raise(subscription_id, investor.id)
        await self._transition_and_unlock(
            subscription,
            "CANCELLED",
            actor_user_id=user_id,
            action="subscriptions.subscription.cancelled",
        )
        return _to_dto(subscription)

    # -- compliance-officer/admin-facing: ops actions + allocation -------------------------------

    async def list_subscriptions_for_series(
        self, series_id: int, *, status: str | None, skip: int, take: int
    ) -> SubscriptionListDto:
        query = (
            self.subscriptions.create_query_builder("sub")
            .left_join_and_select("sub.token_series", "series")
            .left_join_and_select("sub.investor", "investor")
            .where("sub.token_series_id = :series_id", {"series_id": series_id})
        )
        if status:
            query = query.and_where("sub.status = :status", {"status": status})
        subs, total = await query.add_order_by("sub.id", "ASC").skip(skip).take(take).get_many_and_count()
        return SubscriptionListDto(total=total, items=[_to_dto(s) for s in subs])

    async def mark_funded(self, officer_id: int, subscription_id: int) -> SubscriptionResponseDto:
        subscription = await self._get_subscription_or_raise(subscription_id)
        await self._transition(
            subscription, "FUNDED", actor_user_id=officer_id, action="subscriptions.subscription.funded"
        )
        return _to_dto(subscription)

    async def mark_confirmed(self, officer_id: int, subscription_id: int) -> SubscriptionResponseDto:
        subscription = await self._get_subscription_or_raise(subscription_id)
        await self._transition(
            subscription, "CONFIRMED", actor_user_id=officer_id, action="subscriptions.subscription.confirmed"
        )
        return _to_dto(subscription)

    async def refund(self, officer_id: int, subscription_id: int) -> SubscriptionResponseDto:
        """Officer-driven reversal, legal from ``FUNDED`` or ``CONFIRMED`` -- see this module's
        docstring for why this is a deliberate superset of the build plan's diagram. Unlocks the
        full locked amount back to ``available_balance``, atomically with the status flip."""
        subscription = await self._get_subscription_or_raise(subscription_id)
        await self._transition_and_unlock(
            subscription,
            "REFUNDED",
            actor_user_id=officer_id,
            action="subscriptions.subscription.refunded",
        )
        return _to_dto(subscription)

    async def allocate(self, officer_id: int, series_id: int) -> AllocationResultDto:
        """The allocation engine -- a compliance-officer/admin-triggered, synchronous, on-demand
        action (no task-scheduler infra exists yet, see this phase's task brief), not a background
        cron. Requires the proposal's subscription window to have already closed.

        **Pro-rata algorithm**: every currently-``CONFIRMED`` subscription for the series is
        processed in one pass. ``remaining_supply = token_series.total_supply - (units already
        allocated to this series in a prior round)`` -- tracked so a second ``allocate`` call
        (e.g. after more subscriptions reach ``CONFIRMED`` post-window-close) can't over-issue
        beyond ``total_supply``. If ``remaining_supply <= 0`` with ``CONFIRMED`` subscriptions
        still outstanding, this raises ``ConflictException`` rather than silently allocating
        nothing -- those subscriptions need an explicit ``refund`` (see this module's docstring on
        why ``REFUNDED`` is reachable from ``CONFIRMED``). Otherwise ``ratio = min(1,
        remaining_supply / total_requested)`` -- ``1`` (full allocation) when demand doesn't
        exceed remaining supply, ``< 1`` (pro-rata) under oversubscription. Each subscription's
        ``allocated_units = floor(units * ratio, 8dp)`` (``Decimal``/``ROUND_DOWN`` -- never
        over-allocates by a fraction of a unit; the resulting rounding remainder, at most a few
        smallest-unit fractions across the whole series, is intentionally not further redistributed
        -- immaterial at this scale and keeps the algorithm simple/auditable rather than
        implementing a full largest-remainder method).

        For each subscription: the *excess* locked amount (`(units - allocated_units) *
        unit_price_usd`) is unlocked back to `available_balance` (no `LedgerEntry` -- see
        `LedgerService.unlock_within`'s docstring); the *allocated* amount is settled -- consumed
        from `locked_balance` entirely, with a `LedgerEntry` (see `LedgerService.settle_within`'s
        docstring) -- and a `TokenHolding` is created or topped up (see `_upsert_holding`). The
        subscription transitions `CONFIRMED -> ALLOCATED`. All of this -- every subscription's
        status flip, ledger mutation, and holding upsert across the whole series -- happens inside
        one `DataSource.transaction`, per this phase's task brief ("Transitions allocated
        subscriptions to ALLOCATED and creates the corresponding TokenHolding row(s) atomically").
        """
        series = await self._get_series_with_proposal_or_raise(series_id)
        now = _now()
        if now < series.proposal.subscription_end_at:
            raise ConflictException(t("subscriptions.error.subscription_window_still_open"))

        confirmed = await self._list_confirmed_for_series(series_id)
        already_allocated_units = await self._sum_allocated_units_for_series(series_id)
        total_supply = Decimal(str(series.total_supply))
        remaining_supply = total_supply - already_allocated_units

        if not confirmed:
            return AllocationResultDto(
                token_series_id=series_id,
                confirmed_subscription_count=0,
                total_requested_units=0.0,
                remaining_supply_before=float(remaining_supply),
                pro_rata_ratio=None,
                allocated_subscription_count=0,
            )

        if remaining_supply <= 0:
            raise ConflictException(t("subscriptions.error.token_series_fully_allocated"))

        total_requested = sum((Decimal(str(s.units)) for s in confirmed), Decimal("0"))
        ratio = min(Decimal("1"), remaining_supply / total_requested) if total_requested > 0 else Decimal("0")
        unit_price = Decimal(str(series.proposal.unit_price_usd))

        async def work(em: Any) -> int:
            allocated_count = 0
            for subscription in confirmed:
                requested = Decimal(str(subscription.units))
                allocated = (requested * ratio).quantize(_UNITS_QUANT, rounding=ROUND_DOWN)
                if allocated <= 0:
                    continue
                allocated_amount = (allocated * unit_price).quantize(_USD_QUANT, rounding=ROUND_DOWN)
                excess_amount = Decimal(str(subscription.amount_usd)) - allocated_amount

                account = await self.ledger_service.get_or_create_account(subscription.investor)
                if excess_amount > 0:
                    await self.ledger_service.unlock_within(em, account, float(excess_amount))
                await self.ledger_service.settle_within(
                    em, account, float(allocated_amount), reference_id=subscription.id
                )

                await em.update(
                    Subscription,
                    subscription.id,
                    {
                        "status": "ALLOCATED",
                        "allocated_units": float(allocated),
                        "processed_by_user_id": officer_id,
                    },
                )
                await self._upsert_holding(em, subscription.investor, series, float(allocated), float(unit_price))
                allocated_count += 1
            return allocated_count

        allocated_count = await self.ds.transaction(work)

        await self._write_audit_log(
            entity_id=str(series.id),
            actor_user_id=officer_id,
            action="subscriptions.token_series.allocated",
            before_state={"remaining_supply": float(remaining_supply), "confirmed_subscription_count": len(confirmed)},
            after_state={"allocated_subscription_count": allocated_count, "pro_rata_ratio": float(ratio)},
            entity_type="TokenSeries",
        )
        return AllocationResultDto(
            token_series_id=series_id,
            confirmed_subscription_count=len(confirmed),
            total_requested_units=float(total_requested),
            remaining_supply_before=float(remaining_supply),
            pro_rata_ratio=float(ratio),
            allocated_subscription_count=allocated_count,
        )

    # -- internals ------------------------------------------------------------------------------

    async def _upsert_holding(
        self, em: Any, investor: InvestorProfile, series: TokenSeries, allocated_units: float, unit_price: float
    ) -> None:
        """One ``TokenHolding`` row per ``(investor, token_series)`` -- a second subscription
        against a series an investor already holds tops up ``quantity`` and recomputes a
        quantity-weighted ``avg_cost_usd`` rather than inserting a duplicate row."""
        existing = await (
            em.create_query_builder(TokenHolding, "h")
            .where("h.investor_id = :investor_id", {"investor_id": investor.id})
            .and_where("h.token_series_id = :series_id", {"series_id": series.id})
            .get_one()
        )
        if existing is None:
            await em.save(
                TokenHolding(  # type: ignore[call-arg]
                    investor=investor,
                    token_series=series,
                    quantity=allocated_units,
                    avg_cost_usd=unit_price,
                    status="ACTIVE",
                )
            )
            return

        existing_quantity = Decimal(str(existing.quantity))
        existing_avg_cost = Decimal(str(existing.avg_cost_usd))
        added_quantity = Decimal(str(allocated_units))
        new_quantity = existing_quantity + added_quantity
        new_avg_cost = (
            (existing_quantity * existing_avg_cost) + (added_quantity * Decimal(str(unit_price)))
        ) / new_quantity
        await em.update(
            TokenHolding,
            existing.id,
            {
                "quantity": float(new_quantity.quantize(_UNITS_QUANT, rounding=ROUND_DOWN)),
                "avg_cost_usd": float(new_avg_cost.quantize(_USD_QUANT, rounding=ROUND_DOWN)),
            },
        )

    def _assert_transition(self, current_status: str, target_status: str) -> None:
        if target_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
            raise ConflictException(
                t("subscriptions.error.invalid_transition").format(current=current_status, target=target_status)
            )

    async def _transition(
        self, subscription: Subscription, target_status: str, *, actor_user_id: int, action: str
    ) -> None:
        self._assert_transition(subscription.status, target_status)
        before_status = subscription.status
        await self.subscriptions.update(
            {"id": subscription.id}, {"status": target_status, "processed_by_user_id": actor_user_id}
        )
        subscription.status = target_status
        subscription.processed_by_user_id = actor_user_id
        await self._write_audit_log(
            entity_id=str(subscription.id),
            actor_user_id=actor_user_id,
            action=action,
            before_state={"status": before_status},
            after_state={"status": target_status},
        )

    async def _transition_and_unlock(
        self, subscription: Subscription, target_status: str, *, actor_user_id: int, action: str
    ) -> None:
        self._assert_transition(subscription.status, target_status)
        before_status = subscription.status
        account = await self.ledger_service.get_or_create_account(subscription.investor)
        amount = float(subscription.amount_usd)

        async def work(em: Any) -> None:
            await self.ledger_service.unlock_within(em, account, amount)
            await em.update(
                Subscription, subscription.id, {"status": target_status, "processed_by_user_id": actor_user_id}
            )

        await self.ds.transaction(work)
        subscription.status = target_status
        subscription.processed_by_user_id = actor_user_id
        await self._write_audit_log(
            entity_id=str(subscription.id),
            actor_user_id=actor_user_id,
            action=action,
            before_state={"status": before_status},
            after_state={"status": target_status, "unlocked_amount_usd": amount},
        )

    async def _list_confirmed_for_series(self, series_id: int) -> list[Subscription]:
        return await (
            self.subscriptions.create_query_builder("sub")
            .left_join_and_select("sub.investor", "investor")
            .left_join_and_select("sub.token_series", "series")
            .where("sub.token_series_id = :series_id", {"series_id": series_id})
            .and_where("sub.status = :status", {"status": "CONFIRMED"})
            .add_order_by("sub.id", "ASC")
            .get_many()
        )

    async def _sum_allocated_units_for_series(self, series_id: int) -> Decimal:
        allocated = await (
            self.subscriptions.create_query_builder("sub")
            .where("sub.token_series_id = :series_id", {"series_id": series_id})
            .and_where("sub.status = :status", {"status": "ALLOCATED"})
            .get_many()
        )
        return sum((Decimal(str(s.allocated_units or 0)) for s in allocated), Decimal("0"))

    async def _get_investor_by_user_or_raise(self, user_id: int) -> InvestorProfile:
        investor = await (
            self.investor_profiles.create_query_builder("investor")
            .where("investor.user_id = :user_id", {"user_id": user_id})
            .get_one()
        )
        if investor is None:
            raise NotFoundException(t("subscriptions.error.investor_profile_required"))
        return investor

    async def _get_series_with_proposal_or_raise(self, series_id: int) -> TokenSeries:
        # Two single-hop queries, not one three-way chain -- `austial.orm`'s
        # `QueryBuilder.left_join_and_select` only resolves a join's relation name against the
        # *root* entity (see `list_marketplace`'s docstring), so `"p.asset"` off the
        # already-joined (non-root) alias `"p"` raises `RelationNotFoundError`. Same
        # framework-gap workaround as `list_marketplace`.
        series = await (
            self.token_series.create_query_builder("s")
            .left_join_and_select("s.proposal", "p")
            .where("s.id = :id", {"id": series_id})
            .get_one()
        )
        if series is None:
            raise NotFoundException(t("subscriptions.error.token_series_not_found"))
        proposal = await (
            self.proposals.create_query_builder("p")
            .left_join_and_select("p.asset", "asset")
            .left_join_and_select("p.issuer", "issuer")
            .where("p.id = :id", {"id": series.proposal.id})
            .get_one()
        )
        series.proposal = proposal
        return series

    async def _get_subscription_or_raise(self, subscription_id: int) -> Subscription:
        subscription = await self.subscriptions.find_one(
            FindOptions(where={"id": subscription_id}, relations=["investor", "token_series"])
        )
        if subscription is None:
            raise NotFoundException(t("subscriptions.error.subscription_not_found"))
        return subscription

    async def _get_own_subscription_or_raise(self, subscription_id: int, investor_id: int) -> Subscription:
        subscription = await self._get_subscription_or_raise(subscription_id)
        if subscription.investor.id != investor_id:
            # `NotFoundException`, not `ForbiddenException` -- mirrors `AssetsService.
            # _get_own_asset_or_raise`/`IssuanceService._get_own_proposal_or_raise`: don't leak
            # the existence of another investor's subscription.
            raise NotFoundException(t("subscriptions.error.subscription_not_found"))
        return subscription

    async def _write_audit_log(
        self,
        *,
        entity_id: str,
        actor_user_id: int | None,
        action: str,
        before_state: dict[str, Any] | None,
        after_state: dict[str, Any] | None,
        entity_type: str = "Subscription",
    ) -> None:
        await self.audit_logs.save(
            AuditLog(  # type: ignore[call-arg]
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_state=before_state,
                after_state=after_state,
                ip_address=None,
            )
        )
