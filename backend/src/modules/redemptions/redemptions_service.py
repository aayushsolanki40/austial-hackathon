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
from src.modules.ledger.ledger_service import LedgerService
from src.modules.redemptions.entities.distribution import Distribution
from src.modules.redemptions.entities.redemption_request import RedemptionRequest
from src.modules.redemptions.redemptions_dto import (
    CreateDistributionDto,
    CreateRedemptionRequestDto,
    DistributionListDto,
    DistributionResponseDto,
    ProcessDistributionResultDto,
    RedemptionRequestListDto,
    RedemptionRequestResponseDto,
    RejectRedemptionRequestDto,
)
from src.modules.valuation.valuation_service import ValuationService

# Legal status transitions for a `RedemptionRequest` -- see that entity's docstring diagram.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "REQUESTED": {"COMPLIANCE_APPROVED", "REJECTED", "CANCELLED"},
    "COMPLIANCE_APPROVED": {"CUSTODIAN_RELEASED"},
    "CUSTODIAN_RELEASED": {"COMPLETED"},
    "COMPLETED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
}

_UNITS_QUANT = Decimal("0.00000001")  # Numeric(28, 8)
_USD_QUANT = Decimal("0.01")  # Numeric(18, 2)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_request_dto(request: RedemptionRequest) -> RedemptionRequestResponseDto:
    return RedemptionRequestResponseDto(
        id=request.id,
        investor_id=request.investor.id,
        holding_id=request.holding.id,
        token_series_id=request.holding.token_series.id,
        symbol=request.holding.token_series.symbol,
        units_requested=float(request.units_requested),
        nav_per_unit_snapshot=float(request.nav_per_unit_snapshot)
        if request.nav_per_unit_snapshot is not None
        else None,
        payout_amount=float(request.payout_amount) if request.payout_amount is not None else None,
        status=request.status,
        rejection_reason=request.rejection_reason,
        payout_instruction_id=request.payout_instruction_id,
        processed_by_user_id=request.processed_by_user_id,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


def _to_distribution_dto(distribution: Distribution) -> DistributionResponseDto:
    return DistributionResponseDto(
        id=distribution.id,
        token_series_id=distribution.token_series.id,
        total_amount=float(distribution.total_amount),
        currency=distribution.currency,
        record_date=distribution.record_date,
        status=distribution.status,
        triggered_by_user_id=distribution.triggered_by_user_id,
        processed_at=distribution.processed_at,
        created_at=distribution.created_at,
        updated_at=distribution.updated_at,
    )


@Injectable()
class RedemptionsService:
    def __init__(
        self,
        data_source: DataSource,
        ledger_service: LedgerService,
        valuation_service: ValuationService,
        investor_profiles: Repository[InvestorProfile] = InjectRepository(InvestorProfile),
        holdings: Repository[TokenHolding] = InjectRepository(TokenHolding),
        token_series: Repository[TokenSeries] = InjectRepository(TokenSeries),
        redemption_requests: Repository[RedemptionRequest] = InjectRepository(RedemptionRequest),
        distributions: Repository[Distribution] = InjectRepository(Distribution),
        audit_logs: Repository[AuditLog] = InjectRepository(AuditLog),
    ):
        self.ds = data_source
        self.ledger_service = ledger_service
        self.valuation_service = valuation_service
        self.investor_profiles = investor_profiles
        self.holdings = holdings
        self.token_series = token_series
        self.redemption_requests = redemption_requests
        self.distributions = distributions
        self.audit_logs = audit_logs

    # -- investor-facing: request / view / cancel ------------------------------------------------

    async def create_request(self, user_id: int, dto: CreateRedemptionRequestDto) -> RedemptionRequestResponseDto:
        investor = await self._get_investor_by_user_or_raise(user_id)
        holding = await self._get_holding_or_raise(dto.holding_id)
        if holding.investor.id != investor.id:
            # `NotFoundException`, not `ForbiddenException` -- mirrors `HoldingsService.
            # get_my_holding`: don't leak the existence of another investor's holding.
            raise NotFoundException(t("redemptions.error.holding_not_found"))
        if holding.status != "ACTIVE":
            raise ConflictException(t("redemptions.error.holding_not_active"))
        if dto.units_requested > float(holding.quantity):
            raise UnprocessableEntityException(t("redemptions.error.units_exceed_holding"))

        request = await self.redemption_requests.save(
            RedemptionRequest(  # type: ignore[call-arg]
                investor=investor,
                holding=holding,
                units_requested=dto.units_requested,
                status="REQUESTED",
            )
        )
        request.investor = investor
        request.holding = holding

        await self._write_audit_log(
            entity_id=str(request.id),
            actor_user_id=user_id,
            action="redemptions.redemption_request.created",
            before_state=None,
            after_state={"status": "REQUESTED", "units_requested": dto.units_requested},
        )
        return _to_request_dto(request)

    async def list_my_requests(self, user_id: int, *, skip: int, take: int) -> RedemptionRequestListDto:
        investor = await self._get_investor_by_user_or_raise(user_id)
        requests, total = await (
            self._request_query()
            .where("r.investor_id = :investor_id", {"investor_id": investor.id})
            .add_order_by("r.id", "DESC")
            .skip(skip)
            .take(take)
            .get_many_and_count()
        )
        requests = await self._hydrate_holding_series(requests)
        return RedemptionRequestListDto(total=total, items=[_to_request_dto(r) for r in requests])

    async def get_my_request(self, user_id: int, request_id: int) -> RedemptionRequestResponseDto:
        investor = await self._get_investor_by_user_or_raise(user_id)
        request = await self._get_own_request_or_raise(request_id, investor.id)
        return _to_request_dto(request)

    async def cancel_my_request(self, user_id: int, request_id: int) -> RedemptionRequestResponseDto:
        """Investor self-service -- ``REQUESTED`` only, per ``ALLOWED_TRANSITIONS``. Unlike
        ``SubscriptionsService.cancel_my_subscription``, no ledger unlock is needed here -- a
        redemption request never locks funds up front (there is nothing to reverse, only the
        underlying ``TokenHolding`` quantity, which is untouched until ``complete``)."""
        investor = await self._get_investor_by_user_or_raise(user_id)
        request = await self._get_own_request_or_raise(request_id, investor.id)
        await self._transition(
            request, "CANCELLED", actor_user_id=user_id, action="redemptions.redemption_request.cancelled"
        )
        return _to_request_dto(request)

    # -- compliance-officer/admin-facing: review pipeline -----------------------------------------

    async def list_requests(self, *, status: str | None, skip: int, take: int) -> RedemptionRequestListDto:
        query = self._request_query()
        if status:
            query = query.and_where_eq("r.status", status, cast_text=True)
        requests, total = await query.add_order_by("r.id", "ASC").skip(skip).take(take).get_many_and_count()
        requests = await self._hydrate_holding_series(requests)
        return RedemptionRequestListDto(total=total, items=[_to_request_dto(r) for r in requests])

    async def get_request(self, request_id: int) -> RedemptionRequestResponseDto:
        request = await self._get_request_or_raise(request_id)
        return _to_request_dto(request)

    async def approve(self, officer_id: int, request_id: int) -> RedemptionRequestResponseDto:
        """``REQUESTED -> COMPLIANCE_APPROVED``. Snapshots the series' current NAV
        (``ValuationService.get_current_nav``) and the resulting ``payout_amount`` onto the row at
        this instant -- not at request time (the NAV an investor saw when requesting may be stale
        by the time compliance reviews it) and not at completion (an officer approving a redemption
        needs to know, and commit to, the exact payout figure at approval time, not have it drift
        further while custodian release is pending)."""
        request = await self._get_request_or_raise(request_id)
        self._assert_transition(request.status, "COMPLIANCE_APPROVED")

        series_id = request.holding.token_series.id
        nav = await self.valuation_service.get_current_nav(series_id)
        nav_per_unit = Decimal(str(nav.nav_per_unit))
        units = Decimal(str(request.units_requested))
        payout_amount = (units * nav_per_unit).quantize(_USD_QUANT, rounding=ROUND_DOWN)

        await self.redemption_requests.update(
            {"id": request.id},
            {
                "status": "COMPLIANCE_APPROVED",
                "nav_per_unit_snapshot": float(nav_per_unit),
                "payout_amount": float(payout_amount),
                "processed_by_user_id": officer_id,
            },
        )
        request.status = "COMPLIANCE_APPROVED"
        request.nav_per_unit_snapshot = float(nav_per_unit)
        request.payout_amount = float(payout_amount)
        request.processed_by_user_id = officer_id

        await self._write_audit_log(
            entity_id=str(request.id),
            actor_user_id=officer_id,
            action="redemptions.redemption_request.approved",
            before_state={"status": "REQUESTED"},
            after_state={
                "status": "COMPLIANCE_APPROVED",
                "nav_per_unit_snapshot": float(nav_per_unit),
                "payout_amount": float(payout_amount),
            },
        )
        return _to_request_dto(request)

    async def reject(
        self, officer_id: int, request_id: int, dto: RejectRedemptionRequestDto
    ) -> RedemptionRequestResponseDto:
        request = await self._get_request_or_raise(request_id)
        self._assert_transition(request.status, "REJECTED")
        await self.redemption_requests.update(
            {"id": request.id},
            {"status": "REJECTED", "rejection_reason": dto.reason, "processed_by_user_id": officer_id},
        )
        request.status = "REJECTED"
        request.rejection_reason = dto.reason
        request.processed_by_user_id = officer_id

        await self._write_audit_log(
            entity_id=str(request.id),
            actor_user_id=officer_id,
            action="redemptions.redemption_request.rejected",
            before_state={"status": "REQUESTED"},
            after_state={"status": "REJECTED", "rejection_reason": dto.reason},
        )
        return _to_request_dto(request)

    async def release(self, officer_id: int, request_id: int) -> RedemptionRequestResponseDto:
        """``COMPLIANCE_APPROVED -> CUSTODIAN_RELEASED`` -- records that the underlying asset's
        custodian has confirmed the release backing this redemption. No real custodian API exists
        to call (mirrors ``IssuanceService``'s identical "manual/simulated" filing steps), so this
        is a manual ops action gated the same as every other step in this pipeline."""
        request = await self._get_request_or_raise(request_id)
        await self._transition(
            request, "CUSTODIAN_RELEASED", actor_user_id=officer_id, action="redemptions.redemption_request.released"
        )
        return _to_request_dto(request)

    async def complete(self, officer_id: int, request_id: int) -> RedemptionRequestResponseDto:
        """``CUSTODIAN_RELEASED -> COMPLETED`` -- the only step in this pipeline that actually
        moves money. Two-step ledger write, both inside the one atomic transaction: first
        ``LedgerService.credit_within`` lands ``payout_amount`` into the investor's
        ``available_balance`` (``CREDIT_REDEMPTION``, mirrors ``confirm_funding_instruction``'s
        credit shape), then ``debit_payout_within`` immediately pays it back out (``DEBIT_PAYOUT``)
        -- the same two-step "credit in, then debit out" pattern as a funding-then-payout round
        trip, chosen so the payout leaves a normal audit trail through the existing
        ``PayoutInstruction`` machinery rather than inventing a redemption-specific payout record.
        The source ``TokenHolding.quantity`` is shrunk by ``units_requested`` in the same
        transaction, flipping to ``REDEEMED`` if that empties it out entirely -- see
        ``TokenHolding``'s docstring on that status column.
        """
        request = await self._get_request_or_raise(request_id)
        self._assert_transition(request.status, "COMPLETED")

        investor = request.investor
        holding = request.holding
        payout_amount = float(request.payout_amount)
        account = await self.ledger_service.get_or_create_account(investor)

        async def work(em: Any) -> int:
            await self.ledger_service.credit_within(
                em,
                account,
                payout_amount,
                entry_type="CREDIT_REDEMPTION",
                reference_type="REDEMPTION",
                reference_id=request.id,
                idempotency_key=f"redemption:{request.id}:credit",
            )
            payout, _entry = await self.ledger_service.debit_payout_within(
                em,
                account,
                payout_amount,
                investor=investor,
                currency=account.currency,
                memo=f"Redemption #{request.id}",
                officer_id=officer_id,
                idempotency_key=f"redemption:{request.id}:payout",
            )
            new_quantity = Decimal(str(holding.quantity)) - Decimal(str(request.units_requested))
            new_status = "REDEEMED" if new_quantity <= 0 else holding.status
            await em.update(
                TokenHolding,
                holding.id,
                {"quantity": float(new_quantity.quantize(_UNITS_QUANT, rounding=ROUND_DOWN)), "status": new_status},
            )
            await em.update(
                RedemptionRequest,
                request.id,
                {"status": "COMPLETED", "payout_instruction_id": payout.id, "processed_by_user_id": officer_id},
            )
            return payout.id

        payout_instruction_id = await self.ds.transaction(work)
        request.status = "COMPLETED"
        request.payout_instruction_id = payout_instruction_id
        request.processed_by_user_id = officer_id

        await self._write_audit_log(
            entity_id=str(request.id),
            actor_user_id=officer_id,
            action="redemptions.redemption_request.completed",
            before_state={"status": "CUSTODIAN_RELEASED"},
            after_state={"status": "COMPLETED", "payout_amount": payout_amount},
        )
        return _to_request_dto(request)

    # -- distributions ----------------------------------------------------------------------------

    async def create_distribution(self, officer_id: int, dto: CreateDistributionDto) -> DistributionResponseDto:
        series = await self._get_series_or_raise(dto.token_series_id)
        distribution = await self.distributions.save(
            Distribution(  # type: ignore[call-arg]
                token_series=series,
                total_amount=dto.total_amount,
                currency=dto.currency,
                record_date=dto.record_date,
                status="DRAFT",
            )
        )
        distribution.token_series = series

        await self._write_audit_log(
            entity_id=str(distribution.id),
            actor_user_id=officer_id,
            action="redemptions.distribution.created",
            before_state=None,
            after_state={"status": "DRAFT", "total_amount": dto.total_amount},
            entity_type="Distribution",
        )
        return _to_distribution_dto(distribution)

    async def list_distributions(self, *, status: str | None, skip: int, take: int) -> DistributionListDto:
        query = self.distributions.create_query_builder("d").left_join_and_select("d.token_series", "series")
        if status:
            query = query.and_where_eq("d.status", status, cast_text=True)
        distributions, total = await query.add_order_by("d.id", "DESC").skip(skip).take(take).get_many_and_count()
        return DistributionListDto(total=total, items=[_to_distribution_dto(d) for d in distributions])

    async def list_distributions_for_series(
        self, series_id: int, *, skip: int, take: int
    ) -> DistributionListDto:
        distributions, total = await (
            self.distributions.create_query_builder("d")
            .left_join_and_select("d.token_series", "series")
            .where("d.token_series_id = :series_id", {"series_id": series_id})
            .add_order_by("d.id", "DESC")
            .skip(skip)
            .take(take)
            .get_many_and_count()
        )
        return DistributionListDto(total=total, items=[_to_distribution_dto(d) for d in distributions])

    async def get_distribution(self, distribution_id: int) -> DistributionResponseDto:
        distribution = await self._get_distribution_or_raise(distribution_id)
        return _to_distribution_dto(distribution)

    async def process_distribution(self, officer_id: int, distribution_id: int) -> ProcessDistributionResultDto:
        """``DRAFT -> PROCESSING -> COMPLETED``, all inside one atomic transaction (see
        ``Distribution``'s docstring for why there's no separate background-job step). Every
        currently-``ACTIVE`` ``TokenHolding`` on the series is credited its pro-rata share of
        ``total_amount`` -- ``share = total_amount * holding.quantity / total_outstanding``,
        quantized to 2dp with ``ROUND_DOWN``. Pro-rata division on ``Numeric`` amounts does not
        divide evenly, so the *last* holder in iteration order (stable ``id`` ascending) is instead
        credited ``total_amount - sum(every other holder's share)`` -- absorbing the leftover
        cent(s) rather than silently dropping them, keeping ``sum(all shares) == total_amount``
        exactly."""
        distribution = await self._get_distribution_or_raise(distribution_id)
        if distribution.status != "DRAFT":
            raise ConflictException(t("redemptions.error.distribution_not_draft"))

        holdings = await (
            self.holdings.create_query_builder("h")
            .left_join_and_select("h.investor", "investor")
            .where("h.token_series_id = :series_id", {"series_id": distribution.token_series.id})
            .and_where_eq("h.status", "ACTIVE", cast_text=True)
            .add_order_by("h.id", "ASC")
            .get_many()
        )
        if not holdings:
            raise ConflictException(t("redemptions.error.distribution_no_eligible_holders"))

        total_amount = Decimal(str(distribution.total_amount))
        total_outstanding = sum((Decimal(str(h.quantity)) for h in holdings), Decimal("0"))

        async def work(em: Any) -> tuple[int, Decimal]:
            await em.update(Distribution, distribution.id, {"status": "PROCESSING"})
            # `pro_rata_running_total` only accumulates non-last shares -- it exists purely to let
            # the last holder's share absorb the remainder (`total_amount - pro_rata_running_total`,
            # see this method's docstring). `total_credited` is the separate running sum of every
            # share actually credited (including the last), which is what gets returned/reported --
            # keeping these two sums distinct avoids under-counting the last holder's share.
            pro_rata_running_total = Decimal("0")
            total_credited = Decimal("0")
            holder_count = 0
            for index, holding in enumerate(holdings):
                is_last = index == len(holdings) - 1
                if is_last:
                    share = total_amount - pro_rata_running_total
                else:
                    share = (total_amount * Decimal(str(holding.quantity)) / total_outstanding).quantize(
                        _USD_QUANT, rounding=ROUND_DOWN
                    )
                    pro_rata_running_total += share
                if share <= 0:
                    continue
                account = await self.ledger_service.get_or_create_account(holding.investor)
                await self.ledger_service.credit_within(
                    em,
                    account,
                    float(share),
                    entry_type="CREDIT_DISTRIBUTION",
                    reference_type="DISTRIBUTION",
                    reference_id=distribution.id,
                    idempotency_key=f"distribution:{distribution.id}:holding:{holding.id}",
                )
                total_credited += share
                holder_count += 1
            now = _now()
            await em.update(
                Distribution,
                distribution.id,
                {"status": "COMPLETED", "processed_at": now, "triggered_by_user_id": officer_id},
            )
            return holder_count, total_credited

        holder_count, total_credited = await self.ds.transaction(work)
        distribution.status = "COMPLETED"
        distribution.triggered_by_user_id = officer_id

        await self._write_audit_log(
            entity_id=str(distribution.id),
            actor_user_id=officer_id,
            action="redemptions.distribution.processed",
            before_state={"status": "DRAFT"},
            after_state={"status": "COMPLETED", "holder_count": holder_count, "total_credited": float(total_credited)},
            entity_type="Distribution",
        )
        return ProcessDistributionResultDto(
            distribution_id=distribution.id,
            token_series_id=distribution.token_series.id,
            total_amount=float(total_amount),
            holder_count=holder_count,
            total_credited=float(total_credited),
        )

    # -- internals ------------------------------------------------------------------------------

    def _request_query(self) -> Any:
        """Only single-hop joins off the root ``r`` alias -- ``austial.orm``'s
        ``QueryBuilder.left_join_and_select`` resolves every join against the *root* entity, so a
        second-level join like ``"holding.token_series"`` off the already-joined (non-root)
        ``"holding"`` alias raises ``RelationNotFoundError`` (confirmed in ``austial-py/packages/
        orm/src/austial/orm/driver/sqlalchemy_support.py::compile_select``). Same framework gap
        ``SubscriptionsService.list_marketplace`` documents -- ``holding.token_series`` is instead
        hydrated by ``_hydrate_holding_series`` below via a second single-hop query."""
        return (
            self.redemption_requests.create_query_builder("r")
            .left_join_and_select("r.investor", "investor")
            .left_join_and_select("r.holding", "holding")
        )

    async def _hydrate_holding_series(self, requests: list[RedemptionRequest]) -> list[RedemptionRequest]:
        """Second single-hop query per request, merged in Python -- see ``_request_query``'s
        docstring. Page sizes here are small (default 50, mirrors ``SubscriptionsService.
        list_marketplace``'s identical N+1 tradeoff), so this stays a plain loop rather than an
        unsupported multi-value ``IN (...)`` merge."""
        for request in requests:
            holding_with_series = await (
                self.holdings.create_query_builder("h")
                .left_join_and_select("h.token_series", "series")
                .where("h.id = :id", {"id": request.holding.id})
                .get_one()
            )
            request.holding.token_series = holding_with_series.token_series
        return requests

    def _assert_transition(self, current_status: str, target_status: str) -> None:
        if target_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
            raise ConflictException(
                t("redemptions.error.invalid_transition").format(current=current_status, target=target_status)
            )

    async def _transition(
        self, request: RedemptionRequest, target_status: str, *, actor_user_id: int, action: str
    ) -> None:
        self._assert_transition(request.status, target_status)
        before_status = request.status
        await self.redemption_requests.update(
            {"id": request.id}, {"status": target_status, "processed_by_user_id": actor_user_id}
        )
        request.status = target_status
        request.processed_by_user_id = actor_user_id
        await self._write_audit_log(
            entity_id=str(request.id),
            actor_user_id=actor_user_id,
            action=action,
            before_state={"status": before_status},
            after_state={"status": target_status},
        )

    async def _get_investor_by_user_or_raise(self, user_id: int) -> InvestorProfile:
        investor = await (
            self.investor_profiles.create_query_builder("investor")
            .where("investor.user_id = :user_id", {"user_id": user_id})
            .get_one()
        )
        if investor is None:
            raise NotFoundException(t("redemptions.error.investor_profile_required"))
        return investor

    async def _get_holding_or_raise(self, holding_id: int) -> TokenHolding:
        holding = await self.holdings.find_one(
            FindOptions(where={"id": holding_id}, relations=["investor", "token_series"])
        )
        if holding is None:
            raise NotFoundException(t("redemptions.error.holding_not_found"))
        return holding

    async def _get_series_or_raise(self, series_id: int) -> TokenSeries:
        series = await self.token_series.find_one_by({"id": series_id})
        if series is None:
            raise NotFoundException(t("redemptions.error.token_series_not_found"))
        return series

    async def _get_request_or_raise(self, request_id: int) -> RedemptionRequest:
        request = await self._request_query().where("r.id = :id", {"id": request_id}).get_one()
        if request is None:
            raise NotFoundException(t("redemptions.error.request_not_found"))
        (request,) = await self._hydrate_holding_series([request])
        return request

    async def _get_own_request_or_raise(self, request_id: int, investor_id: int) -> RedemptionRequest:
        request = await self._get_request_or_raise(request_id)
        if request.investor.id != investor_id:
            # `NotFoundException`, not `ForbiddenException` -- mirrors `SubscriptionsService.
            # _get_own_subscription_or_raise`: don't leak the existence of another investor's request.
            raise NotFoundException(t("redemptions.error.request_not_found"))
        return request

    async def _get_distribution_or_raise(self, distribution_id: int) -> Distribution:
        distribution = await self.distributions.find_one(
            FindOptions(where={"id": distribution_id}, relations=["token_series"])
        )
        if distribution is None:
            raise NotFoundException(t("redemptions.error.distribution_not_found"))
        return distribution

    async def _write_audit_log(
        self,
        *,
        entity_id: str,
        actor_user_id: int | None,
        action: str,
        before_state: dict[str, Any] | None,
        after_state: dict[str, Any] | None,
        entity_type: str = "RedemptionRequest",
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
