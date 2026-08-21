"""Unit tests for ``IssuersService`` -- Phase 3. Built straight from the DI container against
an in-memory SQLite ``DataSource``, mirroring ``investors_service_spec.py``'s pattern.
"""

from __future__ import annotations

import pytest
from austial import ConflictException, NotFoundException
from austial.orm import DataSource, OrmModule, repository_token
from austial.testing import Test

from src.modules.auth.entities.user import User
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.issuers.entities.issuer import Issuer
from src.modules.issuers.issuers_dto import CreateIssuerDto
from src.modules.issuers.issuers_service import IssuersService

_VALID_DTO = CreateIssuerDto(
    legal_name="Acme Real Estate Ltd", registration_number="RE-12345", registration_jurisdiction="in"
)


async def _build_module():
    module = await Test.create_testing_module(
        imports=[
            OrmModule.for_root(
                type_="sqlite",
                url="sqlite+aiosqlite:///:memory:",
                entities=[User, Issuer, AuditLog],
                synchronize=True,
            ),
            OrmModule.for_feature([User, Issuer, AuditLog]),
        ],
        providers=[IssuersService],
    ).compile()
    await module.get(DataSource).initialize()
    return module


async def _seed_user(module, *, email: str = "issuer@example.com", role: str = "ISSUER") -> User:
    users = module.get(repository_token(User))
    return await users.save(User(email=email, password_hash="hashed", role=role))  # type: ignore[call-arg]


@pytest.mark.asyncio
async def test_create_profile_persists_and_normalizes_jurisdiction():
    module = await _build_module()
    service = module.get(IssuersService)
    user = await _seed_user(module)

    issuer = await service.create_profile(user.id, _VALID_DTO)

    assert issuer.legal_name == "Acme Real Estate Ltd"
    assert issuer.registration_jurisdiction == "IN"
    assert issuer.verification_status == "PENDING"


@pytest.mark.asyncio
async def test_create_profile_rejects_a_second_profile_for_the_same_user():
    module = await _build_module()
    service = module.get(IssuersService)
    user = await _seed_user(module)
    await service.create_profile(user.id, _VALID_DTO)

    with pytest.raises(ConflictException):
        await service.create_profile(user.id, _VALID_DTO)


@pytest.mark.asyncio
async def test_get_my_profile_raises_not_found_when_none_exists():
    module = await _build_module()
    service = module.get(IssuersService)

    with pytest.raises(NotFoundException):
        await service.get_my_profile(999)


@pytest.mark.asyncio
async def test_approve_transitions_pending_to_verified():
    module = await _build_module()
    service = module.get(IssuersService)
    user = await _seed_user(module)
    officer = await _seed_user(module, email="officer@example.com", role="COMPLIANCE_OFFICER")
    issuer = await service.create_profile(user.id, _VALID_DTO)

    approved = await service.approve(officer.id, issuer.id)

    assert approved.verification_status == "VERIFIED"
    assert approved.verified_by_user_id == officer.id
    assert approved.verified_at is not None


@pytest.mark.asyncio
async def test_reject_transitions_pending_to_rejected_with_reason():
    module = await _build_module()
    service = module.get(IssuersService)
    user = await _seed_user(module)
    officer = await _seed_user(module, email="officer2@example.com", role="COMPLIANCE_OFFICER")
    issuer = await service.create_profile(user.id, _VALID_DTO)

    rejected = await service.reject(officer.id, issuer.id, "Failed fit-and-proper check")

    assert rejected.verification_status == "REJECTED"
    assert rejected.rejection_reason == "Failed fit-and-proper check"


@pytest.mark.asyncio
async def test_approve_is_terminal_and_cannot_be_reapproved():
    module = await _build_module()
    service = module.get(IssuersService)
    user = await _seed_user(module)
    officer = await _seed_user(module, email="officer3@example.com", role="COMPLIANCE_OFFICER")
    issuer = await service.create_profile(user.id, _VALID_DTO)
    await service.approve(officer.id, issuer.id)

    with pytest.raises(ConflictException):
        await service.approve(officer.id, issuer.id)


@pytest.mark.asyncio
async def test_approve_writes_an_audit_log_entry():
    module = await _build_module()
    service = module.get(IssuersService)
    user = await _seed_user(module)
    officer = await _seed_user(module, email="officer4@example.com", role="COMPLIANCE_OFFICER")
    issuer = await service.create_profile(user.id, _VALID_DTO)

    await service.approve(officer.id, issuer.id)

    audit_logs = module.get(repository_token(AuditLog))
    logs = await audit_logs.find_by({"entity_type": "Issuer", "entity_id": str(issuer.id)})
    assert len(logs) == 1
    assert logs[0].action == "issuers.issuer.approved"
