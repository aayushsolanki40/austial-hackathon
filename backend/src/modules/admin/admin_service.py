"""``AdminService`` -- Phase 1.10 (backend half of Section 1.5's admin panel).

No entities of its own -- reads/writes the existing ``User``/``InvestorProfile``/``AuditLog``
repositories directly, per the build plan's scope note for this module.
"""

from __future__ import annotations

from austial import Injectable, NotFoundException
from austial.orm import FindOptions, InjectRepository, Repository

from src.i18n.i18n import t
from src.modules.admin.admin_dto import AdminDashboardSummaryDto, AdminUserDto, AdminUserListDto
from src.modules.auth.entities.user import USER_ROLES, User
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.investors.entities.investor_profile import InvestorProfile

_PENDING_KYC_STATUS = "PENDING"


def _to_admin_user_dto(user: User) -> AdminUserDto:
    return AdminUserDto(
        id=user.id, email=user.email, role=user.role, is_active=user.is_active, created_at=user.created_at
    )


@Injectable()
class AdminService:
    def __init__(
        self,
        users: Repository[User] = InjectRepository(User),
        investor_profiles: Repository[InvestorProfile] = InjectRepository(InvestorProfile),
        audit_logs: Repository[AuditLog] = InjectRepository(AuditLog),
    ):
        self.users = users
        self.investor_profiles = investor_profiles
        self.audit_logs = audit_logs

    # -- public API ----------------------------------------------------------------

    async def dashboard_summary(self) -> AdminDashboardSummaryDto:
        investor_count = await self.investor_profiles.count()
        pending_kyc_count = await self.investor_profiles.count(FindOptions(where={"kyc_status": _PENDING_KYC_STATUS}))
        users_by_role = {role: await self.users.count(FindOptions(where={"role": role})) for role in USER_ROLES}
        return AdminDashboardSummaryDto(
            investor_count=investor_count,
            pending_kyc_count=pending_kyc_count,
            users_by_role=users_by_role,
        )

    async def list_users(self, *, search: str | None, skip: int, take: int) -> AdminUserListDto:
        # `Repository.find_by`/`FindOptions.where` only express equality (see
        # `KycVerifiedGuard`'s docstring on this same limitation) -- a partial-match email search
        # needs the raw `QueryBuilder` escape hatch instead. `LOWER(...) LIKE LOWER(...)` rather
        # than Postgres's `ILIKE` -- the app's real database is Postgres, but this app's unit
        # tests deliberately run against an in-memory SQLite `DataSource` for speed/no-live-DB
        # (see `README.md`'s Testing section), and SQLite has no `ILIKE` operator. `LIKE` is
        # already case-insensitive on SQLite by default for ASCII, but explicit `LOWER()` on both
        # sides keeps behavior identical (and correct for non-ASCII) on both dialects.
        query = self.users.create_query_builder("u")
        if search:
            query = query.where("LOWER(u.email) LIKE LOWER(:search)", {"search": f"%{search}%"})
        query = query.add_order_by("u.id", "ASC").skip(skip).take(take)
        users, total = await query.get_many_and_count()
        return AdminUserListDto(total=total, items=[_to_admin_user_dto(user) for user in users])

    async def update_user_role(self, user_id: int, new_role: str, *, actor_user_id: int | None) -> AdminUserDto:
        user = await self._get_user_or_raise(user_id)
        before_state = {"role": user.role}
        user.role = new_role
        updated = await self.users.save(user)
        await self._write_audit_log(
            action="admin.user.role_changed",
            entity_id=str(user_id),
            actor_user_id=actor_user_id,
            before_state=before_state,
            after_state={"role": new_role},
        )
        return _to_admin_user_dto(updated)

    async def suspend_user(self, user_id: int, *, actor_user_id: int | None) -> AdminUserDto:
        user = await self._get_user_or_raise(user_id)
        before_state = {"is_active": user.is_active}
        user.is_active = False
        updated = await self.users.save(user)
        await self._write_audit_log(
            action="admin.user.suspended",
            entity_id=str(user_id),
            actor_user_id=actor_user_id,
            before_state=before_state,
            after_state={"is_active": False},
        )
        return _to_admin_user_dto(updated)

    # -- internals -------------------------------------------------------------------

    async def _get_user_or_raise(self, user_id: int) -> User:
        user = await self.users.find_one_by({"id": user_id})
        if user is None:
            raise NotFoundException(t("admin.error.user_not_found"))
        return user

    async def _write_audit_log(
        self,
        *,
        action: str,
        entity_id: str,
        actor_user_id: int | None,
        before_state: dict,
        after_state: dict,
    ) -> None:
        # In addition to (not instead of) the generic `AuditInterceptor` row every mutating
        # request already produces (see that class's docstring) -- this one carries a real,
        # domain-meaningful before/after diff for a regulator-sensitive action (role change /
        # suspension), which the generic interceptor has no way to know how to compute.
        await self.audit_logs.save(
            # `# type: ignore[call-arg]` -- see the note on `User(...)` in `AuthService.register()`.
            AuditLog(  # type: ignore[call-arg]
                actor_user_id=actor_user_id,
                action=action,
                entity_type="User",
                entity_id=entity_id,
                before_state=before_state,
                after_state=after_state,
                ip_address=None,
            )
        )
