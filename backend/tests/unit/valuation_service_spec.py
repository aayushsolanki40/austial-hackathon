"""Unit tests for ``ValuationService`` -- Phase 7. Exercises the trailing-average anomaly
detection that decides ``PUBLISHED`` vs ``QUARANTINED`` on ingest, the compliance-officer
override, and ``get_current_nav``'s fallback to a series' original ``proposal.unit_price_usd``
when no feed has ever been published. Mirrors ``subscriptions_service_spec.py``'s in-memory-
SQLite seeding pattern.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from austial import ConflictException
from austial.orm import DataSource, OrmModule, repository_token
from austial.testing import Test

from src.modules.assets.entities.asset import Asset
from src.modules.auth.entities.user import User
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.custodians.entities.custodian import Custodian
from src.modules.issuance.entities.smart_contract_deployment import SmartContractDeployment
from src.modules.issuance.entities.token_series import TokenSeries
from src.modules.issuance.entities.tokenization_proposal import TokenizationProposal
from src.modules.issuers.entities.issuer import Issuer
from src.modules.valuation.entities.valuation_feed import ValuationFeed
from src.modules.valuation.valuation_dto import SubmitValuationFeedDto
from src.modules.valuation.valuation_service import ValuationService

_NOW = datetime.now(UTC).replace(tzinfo=None)

_ENTITIES = [
    User,
    Issuer,
    Custodian,
    Asset,
    TokenizationProposal,
    TokenSeries,
    SmartContractDeployment,
    ValuationFeed,
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
        providers=[ValuationService],
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
            subscription_start_at=_NOW - timedelta(days=1),
            subscription_end_at=_NOW + timedelta(days=6),
        )
    )
    series = await series_repo.save(
        TokenSeries(proposal=proposal, symbol=f"SYM{id(module) % 100000}", total_supply=1000, paused=False)  # type: ignore[call-arg]
    )
    series.proposal = proposal
    return series


def _submit_dto(series_id: int, nav_per_unit: float, *, reported_at: datetime) -> SubmitValuationFeedDto:
    return SubmitValuationFeedDto(
        token_series_id=series_id, nav_per_unit=nav_per_unit, source="ADMIN_ENTRY", reported_at=reported_at
    )


@pytest.mark.asyncio
async def test_first_feed_always_publishes_with_no_anomaly_score():
    module = await _build_module()
    service = module.get(ValuationService)
    series = await _seed_series(module)

    feed = await service.submit_feed(1, _submit_dto(series.id, 105.0, reported_at=_NOW))
    assert feed.status == "PUBLISHED"
    assert feed.anomaly_score is None


@pytest.mark.asyncio
async def test_feed_within_threshold_publishes():
    module = await _build_module()
    service = module.get(ValuationService)
    series = await _seed_series(module)

    await service.submit_feed(1, _submit_dto(series.id, 100.0, reported_at=_NOW - timedelta(days=1)))
    feed = await service.submit_feed(1, _submit_dto(series.id, 105.0, reported_at=_NOW))
    assert feed.status == "PUBLISHED"
    assert feed.anomaly_score == pytest.approx(0.05)


@pytest.mark.asyncio
async def test_feed_beyond_threshold_is_quarantined():
    module = await _build_module()
    service = module.get(ValuationService)
    series = await _seed_series(module)

    await service.submit_feed(1, _submit_dto(series.id, 100.0, reported_at=_NOW - timedelta(days=1)))
    feed = await service.submit_feed(1, _submit_dto(series.id, 130.0, reported_at=_NOW))
    assert feed.status == "QUARANTINED"
    assert feed.anomaly_score == pytest.approx(0.3)

    nav = await service.get_current_nav(series.id)
    assert nav.nav_per_unit == 100.0
    assert nav.source == "VALUATION_FEED"


@pytest.mark.asyncio
async def test_approve_quarantined_feed_publishes_it():
    module = await _build_module()
    service = module.get(ValuationService)
    series = await _seed_series(module)

    await service.submit_feed(1, _submit_dto(series.id, 100.0, reported_at=_NOW - timedelta(days=1)))
    quarantined = await service.submit_feed(1, _submit_dto(series.id, 130.0, reported_at=_NOW))
    assert quarantined.status == "QUARANTINED"

    approved = await service.approve_quarantined_feed(2, quarantined.id)
    assert approved.status == "PUBLISHED"
    assert approved.reviewed_by_user_id == 2

    nav = await service.get_current_nav(series.id)
    assert nav.nav_per_unit == 130.0


@pytest.mark.asyncio
async def test_approve_rejects_a_feed_that_is_not_quarantined():
    module = await _build_module()
    service = module.get(ValuationService)
    series = await _seed_series(module)

    feed = await service.submit_feed(1, _submit_dto(series.id, 100.0, reported_at=_NOW))
    with pytest.raises(ConflictException):
        await service.approve_quarantined_feed(2, feed.id)


@pytest.mark.asyncio
async def test_get_current_nav_falls_back_to_proposal_unit_price_when_no_feed_exists():
    module = await _build_module()
    service = module.get(ValuationService)
    series = await _seed_series(module, unit_price=42.5)

    nav = await service.get_current_nav(series.id)
    assert nav.nav_per_unit == 42.5
    assert nav.source == "PROPOSAL_UNIT_PRICE"
    assert nav.as_of is None
