"""``AssetsService`` -- Phase 3. Owns issuer-facing ``Asset`` submission/listing and
``attach_custodian``, which is the service-layer half of the ★ regulatory rule -- *an asset
cannot be tokenized unless its custodian is IFSCA-verified* -- see ``Custodian``'s docstring for
the full two-layer (service + migration-level composite FK) design and ``Asset``'s docstring for
why ``custodian_verified`` is a denormalized snapshot rather than a live join.

Asset *submission* itself does not require the submitting issuer to already be
``VERIFIED`` (that fit-and-proper gate, owned by ``IssuersService``, is a separate concern --
see ``AUSTIAL_BUILD_PLAN.md`` Phase 3). Only ``attach_custodian`` -- the step that actually
marks an asset ``tokenization_ready`` -- is gated, and only on the custodian's own
``ifsca_verified`` flag.
"""

from __future__ import annotations

from austial import ConflictException, Injectable, NotFoundException
from austial.orm import FindOptions, InjectRepository, Repository

from src.i18n.i18n import t
from src.modules.assets.assets_dto import AssetListDto, AssetResponseDto, CreateAssetDto
from src.modules.assets.entities.asset import Asset
from src.modules.custodians.entities.custodian import Custodian
from src.modules.issuers.entities.issuer import Issuer


def _to_dto(asset: Asset) -> AssetResponseDto:
    custodian_id = asset.custodian.id if asset.custodian is not None else None
    return AssetResponseDto(
        id=asset.id,
        issuer_id=asset.issuer.id,
        custodian_id=custodian_id,
        name=asset.name,
        asset_class=asset.asset_class,
        description=asset.description,
        custodian_verified=asset.custodian_verified,
        tokenization_ready=custodian_id is not None,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


@Injectable()
class AssetsService:
    def __init__(
        self,
        assets: Repository[Asset] = InjectRepository(Asset),
        issuers: Repository[Issuer] = InjectRepository(Issuer),
        custodians: Repository[Custodian] = InjectRepository(Custodian),
    ):
        self.assets = assets
        self.issuers = issuers
        self.custodians = custodians

    async def create_asset(self, user_id: int, dto: CreateAssetDto) -> AssetResponseDto:
        issuer = await self._get_issuer_by_user_or_raise(user_id)

        asset = await self.assets.save(
            Asset(  # type: ignore[call-arg]
                issuer=issuer,
                name=dto.name,
                asset_class=dto.asset_class,
                description=dto.description,
                custodian_verified=False,
            )
        )
        return await self._get_own_asset_dto_or_raise(asset.id, user_id)

    async def list_my_assets(self, user_id: int, *, skip: int, take: int) -> AssetListDto:
        issuer = await self._get_issuer_by_user_or_raise(user_id)
        assets, total = await (
            self.assets.create_query_builder("a")
            .left_join_and_select("a.issuer", "issuer")
            .left_join_and_select("a.custodian", "custodian")
            .where("a.issuer_id = :issuer_id", {"issuer_id": issuer.id})
            .add_order_by("a.id", "ASC")
            .skip(skip)
            .take(take)
            .get_many_and_count()
        )
        return AssetListDto(total=total, items=[_to_dto(asset) for asset in assets])

    async def get_my_asset(self, user_id: int, asset_id: int) -> AssetResponseDto:
        return await self._get_own_asset_dto_or_raise(asset_id, user_id)

    async def attach_custodian(self, user_id: int, asset_id: int, custodian_id: int) -> AssetResponseDto:
        asset = await self._get_own_asset_or_raise(asset_id, user_id)
        if asset.custodian is not None:
            raise ConflictException(t("assets.error.custodian_already_attached"))

        custodian = await self.custodians.find_one_by({"id": custodian_id})
        if custodian is None:
            raise NotFoundException(t("assets.error.custodian_not_found"))
        # ★ The regulatory rule, service-layer half -- see this class's docstring and
        # `Custodian`'s docstring for the migration-level (composite FK) half that also catches
        # any race between this check and the `.save()` below.
        if not custodian.ifsca_verified:
            raise ConflictException(t("assets.error.custodian_not_verified"))

        # `.save()`, not `.update()` -- `Repository.update()` cannot set a `ManyToOne` relation's
        # FK column at all (it only ever touches plain `Column()` attributes -- relation FK
        # columns live in `SchemaCatalog`, not `EntityMetadata.columns`). `asset` was loaded with
        # both `issuer` and `custodian` eager-loaded by `_get_own_asset_or_raise` specifically so
        # this full-column `.save()` doesn't null out the unloaded `issuer` relation -- see the
        # identical foot-gun note in `KycService._flip_investor_kyc_status`.
        asset.custodian = custodian
        asset.custodian_verified = True
        saved = await self.assets.save(asset)
        return _to_dto(saved)

    # -- internals ----------------------------------------------------------------------------

    async def _get_issuer_by_user_or_raise(self, user_id: int) -> Issuer:
        issuer = await (
            self.issuers.create_query_builder("issuer")
            .where("issuer.user_id = :user_id", {"user_id": user_id})
            .get_one()
        )
        if issuer is None:
            raise NotFoundException(t("assets.error.issuer_profile_required"))
        return issuer

    async def _get_own_asset_or_raise(self, asset_id: int, user_id: int) -> Asset:
        issuer = await self._get_issuer_by_user_or_raise(user_id)
        asset = await self.assets.find_one(FindOptions(where={"id": asset_id}, relations=["issuer", "custodian"]))
        if asset is None or asset.issuer is None or asset.issuer.id != issuer.id:
            raise NotFoundException(t("assets.error.not_found"))
        return asset

    async def _get_own_asset_dto_or_raise(self, asset_id: int, user_id: int) -> AssetResponseDto:
        asset = await self._get_own_asset_or_raise(asset_id, user_id)
        return _to_dto(asset)
