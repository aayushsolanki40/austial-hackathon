"""Unit tests for ``AdminService`` -- Phase 1.10 (backend half of Section 1.5's
admin panel). Built straight from the DI container against an in-memory
SQLite ``DataSource``, mirroring ``auth_service_spec.py``'s pattern.
"""

from __future__ import annotations

import pytest
from austial import NotFoundException
from austial.orm import DataSource, OrmModule, repository_token
from austial.testing import Test

from src.modules.admin.admin_service import AdminService
from src.modules.auth.entities.refresh_token import RefreshToken
from src.modules.auth.entities.user import User
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.investors.entities.investor_profile import InvestorProfile


async def _build_module():
    module = await Test.create_testing_module(
        imports=[
            OrmModule.for_root(
                type_="sqlite",
                url="sqlite+aiosqlite:///:memory:",
                entities=[User, RefreshToken, InvestorProfile, AuditLog],
                synchronize=True,
            ),
            OrmModule.for_feature([User, InvestorProfile, AuditLog]),
        ],
        providers=[AdminService],
    ).compile()
    await module.get(DataSource).initialize()
    return module


async def _build_service() -> AdminService:
    module = await _build_module()
    return module.get(AdminService)


async def _seed_user(module, *, email: str, role: str = "INVESTOR", is_active: bool = True) -> User:
    users = module.get(repository_token(User))
    return await users.save(User(email=email, password_hash="hashed", role=role, is_active=is_active))  # type: ignore[call-arg]


async def _seed_investor_profile(module, *, user: User, kyc_status: str = "PENDING") -> InvestorProfile:
    profiles = module.get(repository_token(InvestorProfile))
    return await profiles.save(InvestorProfile(user=user, kyc_status=kyc_status))  # type: ignore[call-arg]


@pytest.mark.asyncio
async def test_dashboard_summary_counts_investors_and_pending_kyc():
    module = await _build_module()
    service = module.get(AdminService)

    investor_user = await _seed_user(module, email="investor@example.com", role="INVESTOR")
    await _seed_investor_profile(module, user=investor_user, kyc_status="PENDING")
    verified_user = await _seed_user(module, email="verified@example.com", role="INVESTOR")
    await _seed_investor_profile(module, user=verified_user, kyc_status="VERIFIED")
    await _seed_user(module, email="admin@example.com", role="ADMIN")

    summary = await service.dashboard_summary()

    assert summary.investor_count == 2
    assert summary.pending_kyc_count == 1
    assert summary.users_by_role["INVESTOR"] == 2
    assert summary.users_by_role["ADMIN"] == 1
    assert summary.users_by_role["ISSUER"] == 0
    assert summary.users_by_role["COMPLIANCE_OFFICER"] == 0


@pytest.mark.asyncio
async def test_dashboard_summary_is_zero_on_empty_database():
    service = await _build_service()

    summary = await service.dashboard_summary()

    assert summary.investor_count == 0
    assert summary.pending_kyc_count == 0
    assert all(count == 0 for count in summary.users_by_role.values())


@pytest.mark.asyncio
async def test_list_users_paginates_and_orders_by_id():
    module = await _build_module()
    service = module.get(AdminService)
    for i in range(3):
        await _seed_user(module, email=f"user{i}@example.com")

    page = await service.list_users(search=None, skip=0, take=2)

    assert page.total == 3
    assert len(page.items) == 2
    assert page.items[0].email == "user0@example.com"
    assert page.items[1].email == "user1@example.com"


@pytest.mark.asyncio
async def test_list_users_filters_by_partial_email_match():
    module = await _build_module()
    service = module.get(AdminService)
    await _seed_user(module, email="alice@example.com")
    await _seed_user(module, email="bob@example.com")

    page = await service.list_users(search="alice", skip=0, take=50)

    assert page.total == 1
    assert page.items[0].email == "alice@example.com"


@pytest.mark.asyncio
async def test_update_user_role_writes_before_after_audit_log():
    module = await _build_module()
    service = module.get(AdminService)
    user = await _seed_user(module, email="promote@example.com", role="INVESTOR")

    updated = await service.update_user_role(user.id, "COMPLIANCE_OFFICER", actor_user_id=999)

    assert updated.role == "COMPLIANCE_OFFICER"

    audit_logs = module.get(repository_token(AuditLog))
    logs = await audit_logs.find()
    assert len(logs) == 1
    log = logs[0]
    assert log.action == "admin.user.role_changed"
    assert log.entity_type == "User"
    assert log.entity_id == str(user.id)
    assert log.actor_user_id == 999
    assert log.before_state == {"role": "INVESTOR"}
    assert log.after_state == {"role": "COMPLIANCE_OFFICER"}


@pytest.mark.asyncio
async def test_update_user_role_raises_not_found_for_unknown_user():
    service = await _build_service()

    with pytest.raises(NotFoundException):
        await service.update_user_role(9999, "ADMIN", actor_user_id=1)


@pytest.mark.asyncio
async def test_suspend_user_flips_is_active_and_writes_audit_log():
    module = await _build_module()
    service = module.get(AdminService)
    user = await _seed_user(module, email="suspend@example.com", is_active=True)

    updated = await service.suspend_user(user.id, actor_user_id=1)

    assert updated.is_active is False

    audit_logs = module.get(repository_token(AuditLog))
    logs = await audit_logs.find()
    assert len(logs) == 1
    log = logs[0]
    assert log.action == "admin.user.suspended"
    assert log.before_state == {"is_active": True}
    assert log.after_state == {"is_active": False}


@pytest.mark.asyncio
async def test_suspend_user_raises_not_found_for_unknown_user():
    service = await _build_service()

    with pytest.raises(NotFoundException):
        await service.suspend_user(9999, actor_user_id=1)
