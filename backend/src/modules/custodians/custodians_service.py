"""``CustodiansService`` -- Phase 3. Owns the IFSCA custodian registry: creation and
verification are both ``COMPLIANCE_OFFICER``-gated (see ``CustodiansController``'s docstring for
why compliance, not admin, owns this -- mirrors ``KycController``'s review-queue role split).

``verify()`` is the service-layer half of the "an asset cannot be tokenized unless its custodian
is IFSCA-verified" rule -- see ``Custodian``'s docstring for the DB-level half (a hand-authored
composite FK constraint in the Alembic migration) and ``AssetsService.attach_custodian`` for
where the rule is actually enforced against an ``Asset``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from austial import ConflictException, Injectable, NotFoundException
from austial.orm import InjectRepository, Repository

from src.i18n.i18n import t
from src.modules.custodians.custodians_dto import CreateCustodianDto, CustodianListDto, CustodianResponseDto
from src.modules.custodians.entities.custodian import Custodian


def _to_dto(custodian: Custodian) -> CustodianResponseDto:
    return CustodianResponseDto(
        id=custodian.id,
        name=custodian.name,
        ifsca_registration_no=custodian.ifsca_registration_no,
        ifsca_verified=custodian.ifsca_verified,
        verified_by_user_id=custodian.verified_by_user_id,
        verified_at=custodian.verified_at,
        created_at=custodian.created_at,
        updated_at=custodian.updated_at,
    )


@Injectable()
class CustodiansService:
    def __init__(self, custodians: Repository[Custodian] = InjectRepository(Custodian)):
        self.custodians = custodians

    async def create(self, dto: CreateCustodianDto) -> CustodianResponseDto:
        existing = await self.custodians.find_one_by({"ifsca_registration_no": dto.ifsca_registration_no})
        if existing is not None:
            raise ConflictException(t("custodians.error.registration_no_already_exists"))

        custodian = await self.custodians.save(
            Custodian(  # type: ignore[call-arg]
                name=dto.name, ifsca_registration_no=dto.ifsca_registration_no, ifsca_verified=False
            )
        )
        return _to_dto(custodian)

    async def list(self, *, skip: int, take: int) -> CustodianListDto:
        custodians, total = await (
            self.custodians.create_query_builder("c")
            .add_order_by("c.id", "ASC")
            .skip(skip)
            .take(take)
            .get_many_and_count()
        )
        return CustodianListDto(total=total, items=[_to_dto(custodian) for custodian in custodians])

    async def get_by_id(self, custodian_id: int) -> CustodianResponseDto:
        custodian = await self._get_or_raise(custodian_id)
        return _to_dto(custodian)

    async def verify(self, officer_id: int, custodian_id: int) -> CustodianResponseDto:
        custodian = await self._get_or_raise(custodian_id)
        if custodian.ifsca_verified:
            raise ConflictException(t("custodians.error.already_verified"))

        now = datetime.now(UTC).replace(tzinfo=None)
        await self.custodians.update(
            {"id": custodian.id}, {"ifsca_verified": True, "verified_by_user_id": officer_id, "verified_at": now}
        )
        return await self.get_by_id(custodian.id)

    # -- internals ----------------------------------------------------------------------------

    async def _get_or_raise(self, custodian_id: int) -> Custodian:
        custodian = await self.custodians.find_one_by({"id": custodian_id})
        if custodian is None:
            raise NotFoundException(t("custodians.error.not_found"))
        return custodian
