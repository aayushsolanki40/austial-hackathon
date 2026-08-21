"""Unit tests for ``CustodiansService`` -- Phase 3. Built straight from the DI container against
an in-memory SQLite ``DataSource``, mirroring ``investors_service_spec.py``'s pattern.
"""

from __future__ import annotations

import pytest
from austial import ConflictException, NotFoundException
from austial.orm import DataSource, OrmModule
from austial.testing import Test

from src.modules.custodians.custodians_dto import CreateCustodianDto
from src.modules.custodians.custodians_service import CustodiansService
from src.modules.custodians.entities.custodian import Custodian

_VALID_DTO = CreateCustodianDto(name="GIFT City Custody Services Ltd", ifsca_registration_no="IFSCA-CUST-001")


async def _build_module():
    module = await Test.create_testing_module(
        imports=[
            OrmModule.for_root(
                type_="sqlite",
                url="sqlite+aiosqlite:///:memory:",
                entities=[Custodian],
                synchronize=True,
            ),
            OrmModule.for_feature([Custodian]),
        ],
        providers=[CustodiansService],
    ).compile()
    await module.get(DataSource).initialize()
    return module


@pytest.mark.asyncio
async def test_create_persists_an_unverified_custodian():
    module = await _build_module()
    service = module.get(CustodiansService)

    custodian = await service.create(_VALID_DTO)

    assert custodian.name == "GIFT City Custody Services Ltd"
    assert custodian.ifsca_verified is False
    assert custodian.verified_at is None


@pytest.mark.asyncio
async def test_create_rejects_a_duplicate_registration_number():
    module = await _build_module()
    service = module.get(CustodiansService)
    await service.create(_VALID_DTO)

    with pytest.raises(ConflictException):
        await service.create(_VALID_DTO)


@pytest.mark.asyncio
async def test_get_by_id_raises_not_found_for_unknown_id():
    module = await _build_module()
    service = module.get(CustodiansService)

    with pytest.raises(NotFoundException):
        await service.get_by_id(999)


@pytest.mark.asyncio
async def test_verify_sets_ifsca_verified_and_metadata():
    module = await _build_module()
    service = module.get(CustodiansService)
    custodian = await service.create(_VALID_DTO)

    verified = await service.verify(officer_id=42, custodian_id=custodian.id)

    assert verified.ifsca_verified is True
    assert verified.verified_by_user_id == 42
    assert verified.verified_at is not None


@pytest.mark.asyncio
async def test_verify_is_idempotent_and_rejects_a_second_verification():
    module = await _build_module()
    service = module.get(CustodiansService)
    custodian = await service.create(_VALID_DTO)
    await service.verify(officer_id=42, custodian_id=custodian.id)

    with pytest.raises(ConflictException):
        await service.verify(officer_id=43, custodian_id=custodian.id)


@pytest.mark.asyncio
async def test_list_returns_all_custodians_with_total():
    module = await _build_module()
    service = module.get(CustodiansService)
    await service.create(_VALID_DTO)
    await service.create(CreateCustodianDto(name="Second Custodian", ifsca_registration_no="IFSCA-CUST-002"))

    result = await service.list(skip=0, take=50)

    assert result.total == 2
    assert len(result.items) == 2
