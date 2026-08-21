"""Unit tests for ``IssuanceService`` -- Phase 4. Exercises the
``DRAFT -> DOCUMENTATION_REVIEW -> COMPLIANCE_APPROVED -> IFSCA_FILED -> IFSCA_APPROVED ->
LAUNCHED`` state machine directly (illegal jumps must raise ``ConflictException``), the ★
headline disclosure-completeness gate (``launch`` must refuse until all six ``DisclosureDocument``
types are present-and-current), the ★ tokenization-readiness gate at ``create_proposal``, the
atomic ``TokenSeries`` creation + ``LAUNCHED`` flip, and the circuit-breaker pause/resume pair.
Mirrors ``assets_service_spec.py``'s/``kyc_service_spec.py``'s in-memory-SQLite pattern.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from austial import ConflictException, NotFoundException, UnprocessableEntityException
from austial.orm import DataSource, OrmModule, repository_token
from austial.testing import Test

from src.modules.assets.assets_dto import CreateAssetDto
from src.modules.assets.assets_service import AssetsService
from src.modules.assets.entities.asset import Asset
from src.modules.auth.entities.user import User
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.custodians.custodians_dto import CreateCustodianDto
from src.modules.custodians.custodians_service import CustodiansService
from src.modules.custodians.entities.custodian import Custodian
from src.modules.issuance.entities.disclosure_document import DISCLOSURE_TYPES, DisclosureDocument
from src.modules.issuance.entities.smart_contract_deployment import SmartContractDeployment
from src.modules.issuance.entities.token_series import TokenSeries
from src.modules.issuance.entities.tokenization_proposal import TokenizationProposal
from src.modules.issuance.issuance_dto import (
    AddDisclosureDto,
    CreateProposalDto,
    FileIfscaDto,
    IfscaApproveDto,
    LaunchProposalDto,
    RejectProposalDto,
)
from src.modules.issuance.issuance_service import IssuanceService
from src.modules.issuers.entities.issuer import Issuer
from src.modules.issuers.issuers_dto import CreateIssuerDto
from src.modules.issuers.issuers_service import IssuersService
from src.storage.object_storage_service import ObjectStorageService

_ISSUER_DTO = CreateIssuerDto(
    legal_name="Acme Real Estate Ltd", registration_number="RE-12345", registration_jurisdiction="in"
)
_ASSET_DTO = CreateAssetDto(name="Tower A - Floor 12", asset_class="REAL_ESTATE", description="Prime commercial floor")

_START = datetime(2026, 9, 1, tzinfo=UTC).replace(tzinfo=None)
_END = _START + timedelta(days=30)

_PROPOSAL_DTO = CreateProposalDto(
    asset_id=1,
    total_units=1000,
    unit_price_usd=100,
    min_subscription_units=10,
    subscription_start_at=_START,
    subscription_end_at=_END,
)


class _FakeObjectStorageService:
    """Stands in for ``ObjectStorageService`` -- see ``kyc_service_spec.py``'s identical fake;
    ``IssuanceService`` never inspects the URL's contents, only passes it through."""

    def generate_upload_url(self, object_key: str, *, content_type: str, expires_in: int = 900) -> str:
        return f"https://fake-s3.test/{object_key}?content_type={content_type}"

    def generate_download_url(self, object_key: str, *, expires_in: int = 900) -> str:
        return f"https://fake-s3.test/{object_key}"


async def _build_module():
    module = await Test.create_testing_module(
        imports=[
            OrmModule.for_root(
                type_="sqlite",
                url="sqlite+aiosqlite:///:memory:",
                entities=[
                    User,
                    Issuer,
                    Custodian,
                    Asset,
                    TokenizationProposal,
                    DisclosureDocument,
                    TokenSeries,
                    SmartContractDeployment,
                    AuditLog,
                ],
                synchronize=True,
            ),
            OrmModule.for_feature(
                [
                    User,
                    Issuer,
                    Custodian,
                    Asset,
                    TokenizationProposal,
                    DisclosureDocument,
                    TokenSeries,
                    SmartContractDeployment,
                    AuditLog,
                ]
            ),
        ],
        providers=[
            IssuanceService,
            AssetsService,
            IssuersService,
            CustodiansService,
            {"provide": ObjectStorageService, "useValue": _FakeObjectStorageService()},
        ],
    ).compile()
    await module.get(DataSource).initialize()
    return module


async def _seed_tokenization_ready_asset(module, *, email: str = "issuer@example.com"):
    """Seeds a user -> issuer profile -> asset -> IFSCA-verified custodian attached -- i.e. an
    asset that has already cleared Phase 3's ★ tokenization-readiness gate, mirroring
    ``assets_service_spec.py``'s ``test_attach_custodian_succeeds_once_the_custodian_is_ifsca_
    verified`` setup. ``registration_no`` must be unique per call -- ``CustodiansService.create``
    rejects a duplicate IFSCA registration number, so callers seeding a second asset pass a
    distinct value.
    """
    users = module.get(repository_token(User))
    user = await users.save(User(email=email, password_hash="hashed", role="ISSUER"))  # type: ignore[call-arg]
    issuers_service = module.get(IssuersService)
    await issuers_service.create_profile(user.id, _ISSUER_DTO)
    assets_service = module.get(AssetsService)
    asset = await assets_service.create_asset(user.id, _ASSET_DTO)
    custodians_service = module.get(CustodiansService)
    custodian_dto = CreateCustodianDto(
        name="GIFT City Custody Services Ltd", ifsca_registration_no=f"IFSCA-CUST-{email}"
    )
    custodian = await custodians_service.create(custodian_dto)
    await custodians_service.verify(officer_id=1, custodian_id=custodian.id)
    asset = await assets_service.attach_custodian(user.id, asset.id, custodian.id)
    return user, asset


async def _upload_all_disclosures(service: IssuanceService, user_id: int, proposal_id: int) -> None:
    for disclosure_type in DISCLOSURE_TYPES:
        await service.add_disclosure(
            user_id, proposal_id, AddDisclosureDto(disclosure_type=disclosure_type, object_key=f"key/{disclosure_type}")
        )


async def _create_proposal(module, user_id: int, asset_id: int):
    service = module.get(IssuanceService)
    dto = _PROPOSAL_DTO.model_copy(update={"asset_id": asset_id})
    return await service.create_proposal(user_id, dto)


@pytest.mark.asyncio
async def test_create_proposal_rejects_a_non_tokenization_ready_asset():
    module = await _build_module()
    users = module.get(repository_token(User))
    user = await users.save(User(email="issuer2@example.com", password_hash="x", role="ISSUER"))  # type: ignore[call-arg]
    issuers_service = module.get(IssuersService)
    await issuers_service.create_profile(user.id, _ISSUER_DTO)
    assets_service = module.get(AssetsService)
    asset = await assets_service.create_asset(user.id, _ASSET_DTO)
    issuance_service = module.get(IssuanceService)

    with pytest.raises(ConflictException):
        await issuance_service.create_proposal(user.id, _PROPOSAL_DTO.model_copy(update={"asset_id": asset.id}))


@pytest.mark.asyncio
async def test_create_proposal_succeeds_for_a_tokenization_ready_asset_and_starts_in_draft():
    module = await _build_module()
    user, asset = await _seed_tokenization_ready_asset(module)

    proposal = await _create_proposal(module, user.id, asset.id)

    assert proposal.status == "DRAFT"
    assert proposal.disclosures_complete is False
    assert set(proposal.missing_disclosure_types) == set(DISCLOSURE_TYPES)


@pytest.mark.asyncio
async def test_illegal_transition_is_rejected():
    module = await _build_module()
    user, asset = await _seed_tokenization_ready_asset(module)
    proposal = await _create_proposal(module, user.id, asset.id)
    service = module.get(IssuanceService)

    # DRAFT -> COMPLIANCE_APPROVED skips DOCUMENTATION_REVIEW entirely.
    with pytest.raises(ConflictException):
        await service.compliance_approve(officer_id=1, proposal_id=proposal.id)


@pytest.mark.asyncio
async def test_submit_for_review_moves_draft_to_documentation_review():
    module = await _build_module()
    user, asset = await _seed_tokenization_ready_asset(module)
    proposal = await _create_proposal(module, user.id, asset.id)
    service = module.get(IssuanceService)

    result = await service.submit_for_review(user.id, proposal.id)

    assert result.status == "DOCUMENTATION_REVIEW"


async def _advance_to_ifsca_approved(module, user_id: int, proposal_id: int):
    service = module.get(IssuanceService)
    await service.submit_for_review(user_id, proposal_id)
    await service.compliance_approve(officer_id=1, proposal_id=proposal_id)
    await service.file_with_ifsca(officer_id=1, proposal_id=proposal_id, dto=FileIfscaDto(filing_reference="FIL-001"))
    return await service.ifsca_approve(
        officer_id=1, proposal_id=proposal_id, dto=IfscaApproveDto(approval_reference="APV-001")
    )


@pytest.mark.asyncio
async def test_reject_is_legal_from_documentation_review_and_is_terminal():
    module = await _build_module()
    user, asset = await _seed_tokenization_ready_asset(module)
    proposal = await _create_proposal(module, user.id, asset.id)
    service = module.get(IssuanceService)
    await service.submit_for_review(user.id, proposal.id)

    rejected = await service.reject(officer_id=1, proposal_id=proposal.id, dto=RejectProposalDto(reason="Incomplete"))

    assert rejected.status == "REJECTED"
    with pytest.raises(ConflictException):
        await service.compliance_approve(officer_id=1, proposal_id=proposal.id)


@pytest.mark.asyncio
async def test_reject_is_legal_from_ifsca_filed():
    module = await _build_module()
    user, asset = await _seed_tokenization_ready_asset(module)
    proposal = await _create_proposal(module, user.id, asset.id)
    service = module.get(IssuanceService)
    await service.submit_for_review(user.id, proposal.id)
    await service.compliance_approve(officer_id=1, proposal_id=proposal.id)
    await service.file_with_ifsca(officer_id=1, proposal_id=proposal.id, dto=FileIfscaDto(filing_reference="FIL-002"))

    rejected = await service.reject(
        officer_id=1, proposal_id=proposal.id, dto=RejectProposalDto(reason="Regulator declined")
    )

    assert rejected.status == "REJECTED"


@pytest.mark.asyncio
async def test_launch_is_blocked_until_ifsca_approved_status():
    module = await _build_module()
    user, asset = await _seed_tokenization_ready_asset(module)
    proposal = await _create_proposal(module, user.id, asset.id)
    service = module.get(IssuanceService)

    with pytest.raises(ConflictException):
        await service.launch(officer_id=1, proposal_id=proposal.id, dto=LaunchProposalDto(symbol="ACME1"))


@pytest.mark.asyncio
async def test_launch_is_blocked_when_disclosures_are_incomplete():
    """★ The headline rule of this phase -- see ``DisclosureDocument``'s docstring."""
    module = await _build_module()
    user, asset = await _seed_tokenization_ready_asset(module)
    proposal = await _create_proposal(module, user.id, asset.id)
    await _advance_to_ifsca_approved(module, user.id, proposal.id)
    service = module.get(IssuanceService)
    # Upload five of the six required types -- one short.
    for disclosure_type in DISCLOSURE_TYPES[:-1]:
        await service.add_disclosure(
            user.id, proposal.id, AddDisclosureDto(disclosure_type=disclosure_type, object_key=f"key/{disclosure_type}")
        )

    with pytest.raises(UnprocessableEntityException):
        await service.launch(officer_id=1, proposal_id=proposal.id, dto=LaunchProposalDto(symbol="ACME1"))

    # Proposal status must be unchanged -- the gate rejects before any mutation.
    reloaded = await service.get_proposal(proposal.id)
    assert reloaded.status == "IFSCA_APPROVED"
    series_repo = module.get(repository_token(TokenSeries))
    assert await series_repo.count() == 0


@pytest.mark.asyncio
async def test_launch_succeeds_once_all_six_disclosures_are_current_and_creates_a_token_series():
    module = await _build_module()
    user, asset = await _seed_tokenization_ready_asset(module)
    proposal = await _create_proposal(module, user.id, asset.id)
    await _advance_to_ifsca_approved(module, user.id, proposal.id)
    service = module.get(IssuanceService)
    await _upload_all_disclosures(service, user.id, proposal.id)

    series = await service.launch(officer_id=7, proposal_id=proposal.id, dto=LaunchProposalDto(symbol="ACME1"))

    assert series.symbol == "ACME1"
    assert series.paused is False
    assert series.total_supply == float(_PROPOSAL_DTO.total_units)

    reloaded = await service.get_proposal(proposal.id)
    assert reloaded.status == "LAUNCHED"

    audit_logs = module.get(repository_token(AuditLog))
    actions = [log.action for log in await audit_logs.find()]
    assert "issuance.proposal.launched" in actions


@pytest.mark.asyncio
async def test_launch_rejects_a_duplicate_symbol():
    module = await _build_module()
    user, asset = await _seed_tokenization_ready_asset(module)
    proposal_a = await _create_proposal(module, user.id, asset.id)
    await _advance_to_ifsca_approved(module, user.id, proposal_a.id)
    service = module.get(IssuanceService)
    await _upload_all_disclosures(service, user.id, proposal_a.id)
    await service.launch(officer_id=1, proposal_id=proposal_a.id, dto=LaunchProposalDto(symbol="DUPE1"))

    user_b, asset_b = await _seed_tokenization_ready_asset(module, email="issuer-b@example.com")
    proposal_b = await _create_proposal(module, user_b.id, asset_b.id)
    await _advance_to_ifsca_approved(module, user_b.id, proposal_b.id)
    await _upload_all_disclosures(service, user_b.id, proposal_b.id)

    with pytest.raises(ConflictException):
        await service.launch(officer_id=1, proposal_id=proposal_b.id, dto=LaunchProposalDto(symbol="DUPE1"))


@pytest.mark.asyncio
async def test_disclosure_reupload_supersedes_the_previous_version_without_deleting_it():
    module = await _build_module()
    user, asset = await _seed_tokenization_ready_asset(module)
    proposal = await _create_proposal(module, user.id, asset.id)
    service = module.get(IssuanceService)
    await service.add_disclosure(user.id, proposal.id, AddDisclosureDto(disclosure_type="RISK", object_key="v1"))
    await service.add_disclosure(user.id, proposal.id, AddDisclosureDto(disclosure_type="RISK", object_key="v2"))

    documents = module.get(repository_token(DisclosureDocument))
    rows = await documents.find()
    assert len(rows) == 2  # old row kept, never deleted
    current = [r for r in rows if r.is_current]
    assert len(current) == 1
    assert current[0].object_key == "v2"
    assert current[0].version == 2


@pytest.mark.asyncio
async def test_pause_and_resume_token_series_circuit_breaker():
    module = await _build_module()
    user, asset = await _seed_tokenization_ready_asset(module)
    proposal = await _create_proposal(module, user.id, asset.id)
    await _advance_to_ifsca_approved(module, user.id, proposal.id)
    service = module.get(IssuanceService)
    await _upload_all_disclosures(service, user.id, proposal.id)
    series = await service.launch(officer_id=1, proposal_id=proposal.id, dto=LaunchProposalDto(symbol="PAUS1"))
    assert series.paused is False

    paused = await service.pause_token_series(officer_id=9, series_id=series.id)
    assert paused.paused is True

    with pytest.raises(ConflictException):
        await service.pause_token_series(officer_id=9, series_id=series.id)

    resumed = await service.resume_token_series(officer_id=9, series_id=series.id)
    assert resumed.paused is False


@pytest.mark.asyncio
async def test_get_my_proposal_rejects_access_to_another_issuers_proposal():
    module = await _build_module()
    owner, asset = await _seed_tokenization_ready_asset(module, email="owner@example.com")
    other, _ = await _seed_tokenization_ready_asset(module, email="other@example.com")
    proposal = await _create_proposal(module, owner.id, asset.id)
    service = module.get(IssuanceService)

    with pytest.raises(NotFoundException):
        await service.get_my_proposal(other.id, proposal.id)
