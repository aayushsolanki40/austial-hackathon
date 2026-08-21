"""Unit tests for ``AssetsService`` -- Phase 3. Covers the ★ regulatory rule at the heart of
this phase: ``attach_custodian`` must refuse to attach a custodian whose ``ifsca_verified`` flag
is ``False`` -- see ``Custodian``'s and ``AssetsService``'s docstrings for the full two-layer
(service + migration-level composite FK) design; this file only exercises the service-layer half.
Built straight from the DI container against an in-memory SQLite ``DataSource``, mirroring
``investors_service_spec.py``'s pattern.
"""

from __future__ import annotations

import pytest
from austial import ConflictException, NotFoundException
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
from src.modules.issuers.entities.issuer import Issuer
from src.modules.issuers.issuers_dto import CreateIssuerDto, IssuerResponseDto
from src.modules.issuers.issuers_service import IssuersService

_ISSUER_DTO = CreateIssuerDto(
    legal_name="Acme Real Estate Ltd", registration_number="RE-12345", registration_jurisdiction="in"
)
_CUSTODIAN_DTO = CreateCustodianDto(name="GIFT City Custody Services Ltd", ifsca_registration_no="IFSCA-CUST-001")
_ASSET_DTO = CreateAssetDto(name="Tower A - Floor 12", asset_class="REAL_ESTATE", description="Prime commercial floor")


async def _build_module():
    module = await Test.create_testing_module(
        imports=[
            OrmModule.for_root(
                type_="sqlite",
                url="sqlite+aiosqlite:///:memory:",
                entities=[User, Issuer, Custodian, Asset, AuditLog],
                synchronize=True,
            ),
            OrmModule.for_feature([User, Issuer, Custodian, Asset, AuditLog]),
        ],
        providers=[AssetsService, IssuersService, CustodiansService],
    ).compile()
    await module.get(DataSource).initialize()
    return module


async def _seed_issuer(module, *, email: str = "issuer@example.com") -> tuple[User, IssuerResponseDto]:
    users = module.get(repository_token(User))
    user = await users.save(User(email=email, password_hash="hashed", role="ISSUER"))  # type: ignore[call-arg]
    issuers_service = module.get(IssuersService)
    dto = await issuers_service.create_profile(user.id, _ISSUER_DTO)
    return user, dto


@pytest.mark.asyncio
async def test_create_asset_defaults_to_not_tokenization_ready():
    module = await _build_module()
    service = module.get(AssetsService)
    user, _ = await _seed_issuer(module)

    asset = await service.create_asset(user.id, _ASSET_DTO)

    assert asset.custodian_id is None
    assert asset.custodian_verified is False
    assert asset.tokenization_ready is False


@pytest.mark.asyncio
async def test_create_asset_requires_an_issuer_profile():
    module = await _build_module()
    service = module.get(AssetsService)

    with pytest.raises(NotFoundException):
        await service.create_asset(999, _ASSET_DTO)


@pytest.mark.asyncio
async def test_attach_custodian_rejects_an_unverified_custodian():
    module = await _build_module()
    assets_service = module.get(AssetsService)
    custodians_service = module.get(CustodiansService)
    user, _ = await _seed_issuer(module)
    asset = await assets_service.create_asset(user.id, _ASSET_DTO)
    custodian = await custodians_service.create(_CUSTODIAN_DTO)

    with pytest.raises(ConflictException):
        await assets_service.attach_custodian(user.id, asset.id, custodian.id)

    # Re-fetch to prove the rejected attempt didn't partially persist anything.
    unchanged = await assets_service.get_my_asset(user.id, asset.id)
    assert unchanged.custodian_id is None
    assert unchanged.tokenization_ready is False


@pytest.mark.asyncio
async def test_attach_custodian_succeeds_once_the_custodian_is_ifsca_verified():
    module = await _build_module()
    assets_service = module.get(AssetsService)
    custodians_service = module.get(CustodiansService)
    user, _ = await _seed_issuer(module)
    asset = await assets_service.create_asset(user.id, _ASSET_DTO)
    custodian = await custodians_service.create(_CUSTODIAN_DTO)
    await custodians_service.verify(officer_id=1, custodian_id=custodian.id)

    attached = await assets_service.attach_custodian(user.id, asset.id, custodian.id)

    assert attached.custodian_id == custodian.id
    assert attached.custodian_verified is True
    assert attached.tokenization_ready is True


@pytest.mark.asyncio
async def test_attach_custodian_raises_not_found_for_an_unknown_custodian():
    module = await _build_module()
    assets_service = module.get(AssetsService)
    user, _ = await _seed_issuer(module)
    asset = await assets_service.create_asset(user.id, _ASSET_DTO)

    with pytest.raises(NotFoundException):
        await assets_service.attach_custodian(user.id, asset.id, 999)


@pytest.mark.asyncio
async def test_attach_custodian_rejects_a_second_attachment():
    module = await _build_module()
    assets_service = module.get(AssetsService)
    custodians_service = module.get(CustodiansService)
    user, _ = await _seed_issuer(module)
    asset = await assets_service.create_asset(user.id, _ASSET_DTO)
    custodian_a = await custodians_service.create(_CUSTODIAN_DTO)
    await custodians_service.verify(officer_id=1, custodian_id=custodian_a.id)
    await assets_service.attach_custodian(user.id, asset.id, custodian_a.id)
    custodian_b_dto = CreateCustodianDto(name="Other Custodian", ifsca_registration_no="IFSCA-CUST-002")
    custodian_b = await custodians_service.create(custodian_b_dto)
    await custodians_service.verify(officer_id=1, custodian_id=custodian_b.id)

    with pytest.raises(ConflictException):
        await assets_service.attach_custodian(user.id, asset.id, custodian_b.id)


@pytest.mark.asyncio
async def test_list_my_assets_is_scoped_to_the_owning_issuer():
    module = await _build_module()
    service = module.get(AssetsService)
    user_a, _ = await _seed_issuer(module, email="a@example.com")
    user_b, _ = await _seed_issuer(module, email="b@example.com")
    await service.create_asset(user_a.id, _ASSET_DTO)
    await service.create_asset(user_b.id, _ASSET_DTO)

    assets_a = await service.list_my_assets(user_a.id, skip=0, take=50)

    assert assets_a.total == 1
    assert assets_a.items[0].issuer_id != 0
