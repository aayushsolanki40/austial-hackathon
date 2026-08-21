"""Unit tests for ``InvestorsService`` -- Phase 2. Built straight from the DI container
against an in-memory SQLite ``DataSource``, mirroring ``admin_service_spec.py``'s pattern.
"""

from __future__ import annotations

import pytest
from austial import ConflictException, NotFoundException
from austial.orm import DataSource, OrmModule, repository_token
from austial.testing import Test

from src.modules.auth.entities.user import User
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.investors.entities.wallet_mapping import WalletMapping
from src.modules.investors.investors_dto import CreateInvestorProfileDto, CreateWalletMappingDto
from src.modules.investors.investors_service import InvestorsService


async def _build_module():
    module = await Test.create_testing_module(
        imports=[
            OrmModule.for_root(
                type_="sqlite",
                url="sqlite+aiosqlite:///:memory:",
                entities=[User, InvestorProfile, WalletMapping],
                synchronize=True,
            ),
            OrmModule.for_feature([User, InvestorProfile, WalletMapping]),
        ],
        providers=[InvestorsService],
    ).compile()
    await module.get(DataSource).initialize()
    return module


async def _seed_user(module, *, email: str = "investor@example.com") -> User:
    users = module.get(repository_token(User))
    return await users.save(User(email=email, password_hash="hashed", role="INVESTOR"))  # type: ignore[call-arg]


_VALID_PROFILE_DTO = CreateInvestorProfileDto(investor_type="INDIVIDUAL", jurisdiction="in", risk_profile="MODERATE")


@pytest.mark.asyncio
async def test_create_profile_persists_and_normalizes_jurisdiction():
    module = await _build_module()
    service = module.get(InvestorsService)
    user = await _seed_user(module)

    profile = await service.create_profile(user.id, _VALID_PROFILE_DTO)

    assert profile.investor_type == "INDIVIDUAL"
    assert profile.jurisdiction == "IN"
    assert profile.risk_profile == "MODERATE"
    assert profile.kyc_status == "PENDING"


@pytest.mark.asyncio
async def test_create_profile_rejects_a_second_profile_for_the_same_user():
    module = await _build_module()
    service = module.get(InvestorsService)
    user = await _seed_user(module)
    await service.create_profile(user.id, _VALID_PROFILE_DTO)

    with pytest.raises(ConflictException):
        await service.create_profile(user.id, _VALID_PROFILE_DTO)


@pytest.mark.asyncio
async def test_get_my_profile_raises_not_found_when_none_exists():
    module = await _build_module()
    service = module.get(InvestorsService)

    with pytest.raises(NotFoundException):
        await service.get_my_profile(999)


@pytest.mark.asyncio
async def test_get_my_profile_returns_the_created_profile():
    module = await _build_module()
    service = module.get(InvestorsService)
    user = await _seed_user(module)
    created = await service.create_profile(user.id, _VALID_PROFILE_DTO)

    fetched = await service.get_my_profile(user.id)

    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_add_wallet_mapping_requires_an_existing_profile():
    module = await _build_module()
    service = module.get(InvestorsService)
    user = await _seed_user(module)

    with pytest.raises(NotFoundException):
        await service.add_wallet_mapping(
            user.id, CreateWalletMappingDto(chain="ETHEREUM", address="0xabc123", label="Main")
        )


@pytest.mark.asyncio
async def test_add_and_list_wallet_mappings_are_scoped_to_the_owning_investor():
    module = await _build_module()
    service = module.get(InvestorsService)
    user_a = await _seed_user(module, email="a@example.com")
    user_b = await _seed_user(module, email="b@example.com")
    await service.create_profile(user_a.id, _VALID_PROFILE_DTO)
    await service.create_profile(user_b.id, _VALID_PROFILE_DTO)

    await service.add_wallet_mapping(user_a.id, CreateWalletMappingDto(chain="ETHEREUM", address="0xaaa"))
    await service.add_wallet_mapping(user_a.id, CreateWalletMappingDto(chain="POLYGON", address="0xbbb"))
    await service.add_wallet_mapping(user_b.id, CreateWalletMappingDto(chain="ETHEREUM", address="0xccc"))

    wallets_a = await service.list_wallet_mappings(user_a.id)
    wallets_b = await service.list_wallet_mappings(user_b.id)

    assert len(wallets_a) == 2
    assert {w.address for w in wallets_a} == {"0xaaa", "0xbbb"}
    assert len(wallets_b) == 1
    assert wallets_b[0].address == "0xccc"


@pytest.mark.asyncio
async def test_wallet_mapping_defaults_to_active_status():
    module = await _build_module()
    service = module.get(InvestorsService)
    user = await _seed_user(module)
    await service.create_profile(user.id, _VALID_PROFILE_DTO)

    wallet = await service.add_wallet_mapping(user.id, CreateWalletMappingDto(chain="ETHEREUM", address="0xaaa"))

    assert wallet.status == "ACTIVE"
