from __future__ import annotations
from datetime import UTC, datetime
from statistics import mean
from austial import ConflictException, Injectable, NotFoundException
from austial.orm import FindOptions, InjectRepository, Repository
from src.i18n.i18n import t
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.issuance.entities.token_series import TokenSeries
from src.modules.issuance.entities.tokenization_proposal import TokenizationProposal
from src.modules.valuation.entities.valuation_feed import ValuationFeed
from src.modules.valuation.valuation_dto import (
    CurrentNavResponseDto,
    SubmitValuationFeedDto,
    ValuationFeedListDto,
    ValuationFeedResponseDto,
)

# How many of a series' most-recent `PUBLISHED` feeds form the trailing average a new feed is
# checked against -- small and fixed rather than "all history", so one old outlier can't keep
# distorting the average indefinitely.
_TRAILING_WINDOW_SIZE = 5

# A new feed whose relative deviation from the trailing average exceeds this ratio is quarantined
# rather than published -- see `submit_feed`'s docstring. 15% is a deliberately conservative
# placeholder threshold (no IFSCA-mandated numeric bound exists to calibrate against); tightening/
# loosening this is a product decision, not a regulatory one.
_ANOMALY_DEVIATION_THRESHOLD = 0.15


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_dto(feed: ValuationFeed) -> ValuationFeedResponseDto:
    return ValuationFeedResponseDto(
        id=feed.id,
        token_series_id=feed.token_series.id,
        nav_per_unit=float(feed.nav_per_unit),
        source=feed.source,
        anomaly_score=feed.anomaly_score,
        status=feed.status,
        reported_at=feed.reported_at,
        reviewed_by_user_id=feed.reviewed_by_user_id,
        reviewed_at=feed.reviewed_at,
        created_at=feed.created_at,
    )


@Injectable()
class ValuationService:
    def __init__(
        self,
        token_series: Repository[TokenSeries] = InjectRepository(TokenSeries),
        proposals: Repository[TokenizationProposal] = InjectRepository(TokenizationProposal),
        valuation_feeds: Repository[ValuationFeed] = InjectRepository(ValuationFeed),
        audit_logs: Repository[AuditLog] = InjectRepository(AuditLog),
    ):
        self.token_series = token_series
        self.proposals = proposals
        self.valuation_feeds = valuation_feeds
        self.audit_logs = audit_logs

    async def submit_feed(self, officer_id: int, dto: SubmitValuationFeedDto) -> ValuationFeedResponseDto:
        """Ingests one NAV report. Computes a relative-deviation ``anomaly_score`` against the
        series' trailing average of its last ``_TRAILING_WINDOW_SIZE`` ``PUBLISHED`` feeds
        (ordered by ``reported_at``, not ``created_at`` -- see ``ValuationFeed.reported_at``'s
        docstring) and decides ``status`` from that score *before* the row is ever written --
        never ``PUBLISHED`` then corrected. A series' very first feed (no trailing history to
        compare against) always publishes with ``anomaly_score=None``.
        """
        series = await self._get_series_or_raise(dto.token_series_id)

        trailing = await (
            self.valuation_feeds.create_query_builder("f")
            .where("f.token_series_id = :series_id", {"series_id": series.id})
            .and_where_eq("f.status", "PUBLISHED", cast_text=True)
            .add_order_by("f.reported_at", "DESC")
            .take(_TRAILING_WINDOW_SIZE)
            .get_many()
        )

        anomaly_score: float | None = None
        status = "PUBLISHED"
        if trailing:
            trailing_avg = mean(float(f.nav_per_unit) for f in trailing)
            anomaly_score = abs(dto.nav_per_unit - trailing_avg) / trailing_avg
            status = "QUARANTINED" if anomaly_score > _ANOMALY_DEVIATION_THRESHOLD else "PUBLISHED"

        feed = await self.valuation_feeds.save(
            ValuationFeed(  # type: ignore[call-arg]
                token_series=series,
                nav_per_unit=dto.nav_per_unit,
                source=dto.source,
                anomaly_score=anomaly_score,
                status=status,
                reported_at=dto.reported_at,
            )
        )
        feed.token_series = series

        await self._write_audit_log(
            entity_id=str(feed.id),
            actor_user_id=officer_id,
            action="valuation.valuation_feed.submitted",
            before_state=None,
            after_state={"status": status, "anomaly_score": anomaly_score, "nav_per_unit": dto.nav_per_unit},
        )
        return _to_dto(feed)

    async def approve_quarantined_feed(self, officer_id: int, feed_id: int) -> ValuationFeedResponseDto:
        """Compliance-officer override -- ``QUARANTINED`` only, per this module's docstring.
        Publishes the feed as-is; ``reviewed_by_user_id``/``reviewed_at`` record who overrode it
        and when, mirroring ``TokenizationProposal.reviewed_by_user_id``'s convention."""
        feed = await self._get_feed_or_raise(feed_id)
        if feed.status != "QUARANTINED":
            raise ConflictException(t("valuation.error.feed_not_quarantined"))

        now = _now()
        await self.valuation_feeds.update(
            {"id": feed.id}, {"status": "PUBLISHED", "reviewed_by_user_id": officer_id, "reviewed_at": now}
        )
        feed.status = "PUBLISHED"
        feed.reviewed_by_user_id = officer_id
        feed.reviewed_at = now

        await self._write_audit_log(
            entity_id=str(feed.id),
            actor_user_id=officer_id,
            action="valuation.valuation_feed.approved",
            before_state={"status": "QUARANTINED"},
            after_state={"status": "PUBLISHED"},
        )
        return _to_dto(feed)

    async def list_feeds_for_series(
        self, series_id: int, *, status: str | None, skip: int, take: int
    ) -> ValuationFeedListDto:
        query = (
            self.valuation_feeds.create_query_builder("f")
            .left_join_and_select("f.token_series", "series")
            .where("f.token_series_id = :series_id", {"series_id": series_id})
        )
        if status:
            query = query.and_where_eq("f.status", status, cast_text=True)
        feeds, total = await query.add_order_by("f.reported_at", "DESC").skip(skip).take(take).get_many_and_count()
        return ValuationFeedListDto(total=total, items=[_to_dto(f) for f in feeds])

    async def get_feed(self, feed_id: int) -> ValuationFeedResponseDto:
        feed = await self._get_feed_or_raise(feed_id)
        return _to_dto(feed)

    async def get_current_nav(self, series_id: int) -> CurrentNavResponseDto:
        """"What's this series worth right now" -- the most recent ``PUBLISHED`` feed by
        ``reported_at``, or a fallback to the series' original ``proposal.unit_price_usd`` when no
        feed has ever been published for it yet (see ``ValuationFeed``'s docstring: a series can
        launch and start trading before its first NAV report ever lands). Consumed by
        ``RedemptionsService.approve`` to snapshot a redemption's payout figure."""
        series = await self._get_series_or_raise(series_id)
        latest = await (
            self.valuation_feeds.create_query_builder("f")
            .where("f.token_series_id = :series_id", {"series_id": series.id})
            .and_where_eq("f.status", "PUBLISHED", cast_text=True)
            .add_order_by("f.reported_at", "DESC")
            .get_one()
        )
        if latest is not None:
            return CurrentNavResponseDto(
                token_series_id=series_id, nav_per_unit=float(latest.nav_per_unit), source="VALUATION_FEED",
                as_of=latest.reported_at,
            )

        proposal = await self.proposals.find_one_by({"id": series.proposal.id})
        return CurrentNavResponseDto(
            token_series_id=series_id,
            nav_per_unit=float(proposal.unit_price_usd),
            source="PROPOSAL_UNIT_PRICE",
            as_of=None,
        )

    # -- internals ------------------------------------------------------------------------------

    async def _get_series_or_raise(self, series_id: int) -> TokenSeries:
        series = await self.token_series.find_one(FindOptions(where={"id": series_id}, relations=["proposal"]))
        if series is None:
            raise NotFoundException(t("valuation.error.token_series_not_found"))
        return series

    async def _get_feed_or_raise(self, feed_id: int) -> ValuationFeed:
        feed = await self.valuation_feeds.find_one(
            FindOptions(where={"id": feed_id}, relations=["token_series"])
        )
        if feed is None:
            raise NotFoundException(t("valuation.error.feed_not_found"))
        return feed

    async def _write_audit_log(
        self,
        *,
        entity_id: str,
        actor_user_id: int | None,
        action: str,
        before_state: dict | None,
        after_state: dict | None,
    ) -> None:
        await self.audit_logs.save(
            AuditLog(  # type: ignore[call-arg]
                actor_user_id=actor_user_id,
                action=action,
                entity_type="ValuationFeed",
                entity_id=entity_id,
                before_state=before_state,
                after_state=after_state,
                ip_address=None,
            )
        )
