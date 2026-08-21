"""``IssuersService`` -- Phase 3. Owns ``Issuer`` self-service creation/lookup (one issuer
organisation per ``ISSUER`` user, checked here rather than via a DB constraint -- see the
entity's docstring) plus the ``COMPLIANCE_OFFICER``-facing fit-and-proper review queue
(``PENDING -> VERIFIED | REJECTED``), mirroring ``KycService``'s investor-facing /
compliance-facing split and its explicit ``AuditLog`` writes for regulator-sensitive actions.
"""

from __future__ import annotations

from datetime import UTC, datetime

from austial import ConflictException, Injectable, NotFoundException
from austial.orm import FindOptions, InjectRepository, Repository

from src.i18n.i18n import t
from src.modules.auth.entities.user import User
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.issuers.entities.issuer import Issuer
from src.modules.issuers.issuers_dto import CreateIssuerDto, IssuerListDto, IssuerResponseDto

# Single-hop, terminal both ways -- no automated pre-screening stage the way `KycSubmission`
# has, just a human fit-and-proper review -- see `Issuer`'s docstring.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"VERIFIED", "REJECTED"},
    "VERIFIED": set(),
    "REJECTED": set(),
}


def _to_dto(issuer: Issuer) -> IssuerResponseDto:
    return IssuerResponseDto(
        id=issuer.id,
        legal_name=issuer.legal_name,
        registration_number=issuer.registration_number,
        registration_jurisdiction=issuer.registration_jurisdiction,
        verification_status=issuer.verification_status,
        verified_by_user_id=issuer.verified_by_user_id,
        verified_at=issuer.verified_at,
        rejection_reason=issuer.rejection_reason,
        created_at=issuer.created_at,
        updated_at=issuer.updated_at,
    )


@Injectable()
class IssuersService:
    def __init__(
        self,
        users: Repository[User] = InjectRepository(User),
        issuers: Repository[Issuer] = InjectRepository(Issuer),
        audit_logs: Repository[AuditLog] = InjectRepository(AuditLog),
    ):
        self.users = users
        self.issuers = issuers
        self.audit_logs = audit_logs

    # -- issuer self-service -----------------------------------------------------------------

    async def create_profile(self, user_id: int, dto: CreateIssuerDto) -> IssuerResponseDto:
        existing = await self._find_issuer_by_user(user_id)
        if existing is not None:
            raise ConflictException(t("issuers.error.profile_already_exists"))

        user = await self.users.find_one_by({"id": user_id})
        if user is None:
            # Unreachable in practice -- `user_id` comes from a verified JWT `sub` claim -- see
            # the identical note on `InvestorsService.create_profile`.
            raise NotFoundException(t("issuers.error.user_not_found"))

        issuer = await self.issuers.save(
            Issuer(  # type: ignore[call-arg]
                user=user,
                legal_name=dto.legal_name,
                registration_number=dto.registration_number,
                registration_jurisdiction=dto.registration_jurisdiction,
                verification_status="PENDING",
            )
        )
        return _to_dto(issuer)

    async def get_my_profile(self, user_id: int) -> IssuerResponseDto:
        issuer = await self._get_issuer_by_user_or_raise(user_id)
        return _to_dto(issuer)

    # -- compliance-officer-facing (fit-and-proper review) -----------------------------------

    async def list_pending_review(self, *, skip: int, take: int) -> IssuerListDto:
        issuers, total = await (
            self.issuers.create_query_builder("i")
            .where("i.verification_status = :status", {"status": "PENDING"})
            .add_order_by("i.id", "ASC")
            .skip(skip)
            .take(take)
            .get_many_and_count()
        )
        return IssuerListDto(total=total, items=[_to_dto(issuer) for issuer in issuers])

    async def approve(self, officer_id: int, issuer_id: int) -> IssuerResponseDto:
        issuer = await self._get_issuer_or_raise(issuer_id)
        self._assert_transition(issuer.verification_status, "VERIFIED")

        before_state = {"verification_status": issuer.verification_status}
        now = datetime.now(UTC).replace(tzinfo=None)
        await self.issuers.update(
            {"id": issuer.id},
            {"verification_status": "VERIFIED", "verified_by_user_id": officer_id, "verified_at": now},
        )
        await self._write_audit_log(
            issuer_id=issuer.id,
            actor_user_id=officer_id,
            action="issuers.issuer.approved",
            before_state=before_state,
            after_state={"verification_status": "VERIFIED"},
        )
        return await self.get_by_id(issuer.id)

    async def reject(self, officer_id: int, issuer_id: int, reason: str) -> IssuerResponseDto:
        issuer = await self._get_issuer_or_raise(issuer_id)
        self._assert_transition(issuer.verification_status, "REJECTED")

        before_state = {"verification_status": issuer.verification_status}
        await self.issuers.update(
            {"id": issuer.id},
            {"verification_status": "REJECTED", "verified_by_user_id": officer_id, "rejection_reason": reason},
        )
        await self._write_audit_log(
            issuer_id=issuer.id,
            actor_user_id=officer_id,
            action="issuers.issuer.rejected",
            before_state=before_state,
            after_state={"verification_status": "REJECTED", "rejection_reason": reason},
        )
        return await self.get_by_id(issuer.id)

    async def get_by_id(self, issuer_id: int) -> IssuerResponseDto:
        issuer = await self._get_issuer_or_raise(issuer_id)
        return _to_dto(issuer)

    # -- internals ----------------------------------------------------------------------------

    def _assert_transition(self, current_status: str, target_status: str) -> None:
        if target_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
            raise ConflictException(
                t("issuers.error.invalid_transition").format(current=current_status, target=target_status)
            )

    async def _find_issuer_by_user(self, user_id: int) -> Issuer | None:
        return await (
            self.issuers.create_query_builder("issuer")
            .where("issuer.user_id = :user_id", {"user_id": user_id})
            .get_one()
        )

    async def _get_issuer_by_user_or_raise(self, user_id: int) -> Issuer:
        issuer = await self._find_issuer_by_user(user_id)
        if issuer is None:
            raise NotFoundException(t("issuers.error.profile_not_found"))
        return issuer

    async def _get_issuer_or_raise(self, issuer_id: int) -> Issuer:
        issuer = await self.issuers.find_one(FindOptions(where={"id": issuer_id}))
        if issuer is None:
            raise NotFoundException(t("issuers.error.profile_not_found"))
        return issuer

    async def _write_audit_log(
        self, *, issuer_id: int, actor_user_id: int | None, action: str, before_state: dict, after_state: dict
    ) -> None:
        await self.audit_logs.save(
            AuditLog(  # type: ignore[call-arg]
                actor_user_id=actor_user_id,
                action=action,
                entity_type="Issuer",
                entity_id=str(issuer_id),
                before_state=before_state,
                after_state=after_state,
                ip_address=None,
            )
        )
