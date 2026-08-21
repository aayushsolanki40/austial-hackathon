"""``InvestorsService`` -- Phase 2. Owns ``InvestorProfile`` creation/lookup and
``WalletMapping`` creation/listing for the *current* investor (the ``/investors/*``
routes are all self-service -- an investor manages their own profile/wallets, there is
no "manage someone else's profile" surface in this module; that's ``AdminController``'s
job for role/suspension management instead).

Kept deliberately separate from ``KycService``: this module is the investor
*classification* record (type/jurisdiction/risk profile) an investor sets up once,
independent of whether a ``KycSubmission`` has ever been filed -- ``KycVerifiedGuard``
already treats "no ``InvestorProfile`` row" as "not verified" (see that guard's
docstring), so profile creation is intentionally allowed before KYC is verified.
"""

from __future__ import annotations

from austial import ConflictException, Injectable, NotFoundException
from austial.orm import InjectRepository, Repository

from src.i18n.i18n import t
from src.modules.auth.entities.user import User
from src.modules.investors.entities.investor_profile import InvestorProfile
from src.modules.investors.entities.wallet_mapping import WalletMapping
from src.modules.investors.investors_dto import (
    CreateInvestorProfileDto,
    CreateWalletMappingDto,
    InvestorProfileResponseDto,
    WalletMappingResponseDto,
)


def _to_profile_dto(profile: InvestorProfile) -> InvestorProfileResponseDto:
    return InvestorProfileResponseDto(
        id=profile.id,
        investor_type=profile.investor_type,
        jurisdiction=profile.jurisdiction,
        risk_profile=profile.risk_profile,
        kyc_status=profile.kyc_status,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _to_wallet_dto(wallet: WalletMapping) -> WalletMappingResponseDto:
    return WalletMappingResponseDto(
        id=wallet.id,
        chain=wallet.chain,
        address=wallet.address,
        label=wallet.label,
        status=wallet.status,
        created_at=wallet.created_at,
    )


@Injectable()
class InvestorsService:
    def __init__(
        self,
        users: Repository[User] = InjectRepository(User),
        investor_profiles: Repository[InvestorProfile] = InjectRepository(InvestorProfile),
        wallet_mappings: Repository[WalletMapping] = InjectRepository(WalletMapping),
    ):
        self.users = users
        self.investor_profiles = investor_profiles
        self.wallet_mappings = wallet_mappings

    # -- public API ----------------------------------------------------------------

    async def create_profile(self, user_id: int, dto: CreateInvestorProfileDto) -> InvestorProfileResponseDto:
        existing = await self._find_profile(user_id)
        if existing is not None:
            raise ConflictException(t("investors.error.profile_already_exists"))

        user = await self.users.find_one_by({"id": user_id})
        if user is None:
            # Unreachable in practice -- `user_id` comes from a verified JWT `sub` claim -- but
            # guards against a deleted-user edge case rather than crashing on `None`.
            raise NotFoundException(t("investors.error.user_not_found"))

        profile = await self.investor_profiles.save(
            # `# type: ignore[call-arg]` -- see the note on `User(...)` in `AuthService.register()`
            # (`austial-py` `py.typed` gap, tracked for `austial-framework-dev`).
            InvestorProfile(  # type: ignore[call-arg]
                user=user,
                investor_type=dto.investor_type,
                jurisdiction=dto.jurisdiction,
                risk_profile=dto.risk_profile,
                kyc_status="PENDING",
            )
        )
        return _to_profile_dto(profile)

    async def get_my_profile(self, user_id: int) -> InvestorProfileResponseDto:
        profile = await self._get_profile_or_raise(user_id)
        return _to_profile_dto(profile)

    async def add_wallet_mapping(self, user_id: int, dto: CreateWalletMappingDto) -> WalletMappingResponseDto:
        profile = await self._get_profile_or_raise(user_id)
        wallet = await self.wallet_mappings.save(
            WalletMapping(  # type: ignore[call-arg]
                investor=profile,
                chain=dto.chain,
                address=dto.address,
                label=dto.label,
                status="ACTIVE",
            )
        )
        return _to_wallet_dto(wallet)

    async def list_wallet_mappings(self, user_id: int) -> list[WalletMappingResponseDto]:
        profile = await self._get_profile_or_raise(user_id)
        wallets = await (
            self.wallet_mappings.create_query_builder("w")
            .where("w.investor_id = :investor_id", {"investor_id": profile.id})
            .add_order_by("w.id", "ASC")
            .get_many()
        )
        return [_to_wallet_dto(wallet) for wallet in wallets]

    # -- internals -------------------------------------------------------------------

    async def _find_profile(self, user_id: int) -> InvestorProfile | None:
        return await (
            self.investor_profiles.create_query_builder("investor_profile")
            .where("investor_profile.user_id = :user_id", {"user_id": user_id})
            .get_one()
        )

    async def _get_profile_or_raise(self, user_id: int) -> InvestorProfile:
        profile = await self._find_profile(user_id)
        if profile is None:
            raise NotFoundException(t("investors.error.profile_not_found"))
        return profile
