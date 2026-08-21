"""``IssuanceService`` -- Phase 4. Owns the ``TokenizationProposal`` state machine::

    DRAFT -> DOCUMENTATION_REVIEW -> COMPLIANCE_APPROVED -> IFSCA_FILED
          -> IFSCA_APPROVED -> LAUNCHED
                            \\-> REJECTED (terminal)

Every transition is (a) checked against ``ALLOWED_TRANSITIONS`` -- an illegal jump raises
``ConflictException`` rather than silently applying, mirroring ``KycService``'s/``IssuersService``'s
identical convention -- and (b) written to ``AuditLog`` directly (in addition to, not instead of,
the generic global ``AuditInterceptor`` every mutating request already produces).

``file_with_ifsca``/``ifsca_approve`` model IFSCA's regulatory filing/approval as a manual,
compliance-officer-recorded action (a reference string the officer types in), **not** a real
external API call -- no such API exists (see ``AUSTIAL_BUILD_PLAN.md``'s note: "manual/simulated
-- no real IFSCA API exists, model this as a compliance-officer or admin action recording the
filing, not an actual external call").

★ The headline rule of this phase -- ``launch`` is unreachable unless all six ``DisclosureDocument``
types are present-and-current -- lives in ``launch`` below, essentially the plan's own code
sketch: check ``proposal.status == "IFSCA_APPROVED"``, check disclosure completeness, then
atomically create ``TokenSeries`` + flip the proposal's status via ``DataSource.transaction``.

★ Tokenization-readiness gate -- see ``TokenizationProposal``'s docstring for why this is enforced
once, at ``create_proposal``, rather than re-derived at every later transition.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from austial import ConflictException, Injectable, NotFoundException, UnprocessableEntityException
from austial.orm import DataSource, FindOptions, InjectRepository, Repository

from src.i18n.i18n import t
from src.modules.assets.entities.asset import Asset
from src.modules.compliance.entities.audit_log import AuditLog
from src.modules.issuance.entities.disclosure_document import DISCLOSURE_TYPES, DisclosureDocument
from src.modules.issuance.entities.smart_contract_deployment import SmartContractDeployment
from src.modules.issuance.entities.token_series import TokenSeries
from src.modules.issuance.entities.tokenization_proposal import TokenizationProposal
from src.modules.issuance.issuance_dto import (
    AddDisclosureDto,
    CreateProposalDto,
    DisclosureDocumentResponseDto,
    DisclosureUploadUrlRequestDto,
    DisclosureUploadUrlResponseDto,
    FileIfscaDto,
    IfscaApproveDto,
    LaunchProposalDto,
    ProposalDetailResponseDto,
    ProposalListDto,
    ProposalResponseDto,
    RecordSmartContractDeploymentDto,
    RejectProposalDto,
    SmartContractDeploymentResponseDto,
    TokenSeriesResponseDto,
)
from src.modules.issuers.entities.issuer import Issuer
from src.storage.object_storage_service import ObjectStorageService

# Legal status transitions -- anything not listed here (including no-op "transitions" to the
# current status) is rejected by `_assert_transition`. Both `DOCUMENTATION_REVIEW` and
# `IFSCA_FILED` can end in `REJECTED` -- see the state diagram in this module's docstring.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"DOCUMENTATION_REVIEW"},
    "DOCUMENTATION_REVIEW": {"COMPLIANCE_APPROVED", "REJECTED"},
    "COMPLIANCE_APPROVED": {"IFSCA_FILED"},
    "IFSCA_FILED": {"IFSCA_APPROVED", "REJECTED"},
    "IFSCA_APPROVED": {"LAUNCHED"},
    "LAUNCHED": set(),
    "REJECTED": set(),
}

# ★ The completeness gate -- see this module's and `DisclosureDocument`'s docstrings.
REQUIRED_DISCLOSURES = ("RISK", "FEE", "LIQUIDITY", "CUSTODY", "TAX", "PROSPECTUS")

assert set(REQUIRED_DISCLOSURES) == set(DISCLOSURE_TYPES)  # kept in lockstep, deliberately


def _to_proposal_dto(proposal: TokenizationProposal) -> ProposalResponseDto:
    return ProposalResponseDto(
        id=proposal.id,
        asset_id=proposal.asset.id,
        issuer_id=proposal.issuer.id,
        total_units=float(proposal.total_units),
        unit_price_usd=float(proposal.unit_price_usd),
        min_subscription_units=float(proposal.min_subscription_units),
        subscription_start_at=proposal.subscription_start_at,
        subscription_end_at=proposal.subscription_end_at,
        status=proposal.status,
        ifsca_filing_reference=proposal.ifsca_filing_reference,
        ifsca_approval_reference=proposal.ifsca_approval_reference,
        rejection_reason=proposal.rejection_reason,
        reviewed_by_user_id=proposal.reviewed_by_user_id,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
    )


def _to_disclosure_dto(document: DisclosureDocument) -> DisclosureDocumentResponseDto:
    return DisclosureDocumentResponseDto(
        id=document.id,
        disclosure_type=document.disclosure_type,
        object_key=document.object_key,
        version=document.version,
        is_current=document.is_current,
        created_at=document.created_at,
    )


def _to_series_dto(series: TokenSeries) -> TokenSeriesResponseDto:
    deployment_id = series.smart_contract_deployment.id if series.smart_contract_deployment is not None else None
    return TokenSeriesResponseDto(
        id=series.id,
        proposal_id=series.proposal.id,
        symbol=series.symbol,
        total_supply=float(series.total_supply),
        contract_address=series.contract_address,
        paused=series.paused,
        smart_contract_deployment_id=deployment_id,
        created_at=series.created_at,
        updated_at=series.updated_at,
    )


def _to_deployment_dto(deployment: SmartContractDeployment) -> SmartContractDeploymentResponseDto:
    return SmartContractDeploymentResponseDto(
        id=deployment.id,
        bytecode_hash=deployment.bytecode_hash,
        version=deployment.version,
        audit_report_ref=deployment.audit_report_ref,
        deployed_at=deployment.deployed_at,
        created_at=deployment.created_at,
    )


@Injectable()
class IssuanceService:
    def __init__(
        self,
        storage: ObjectStorageService,
        data_source: DataSource,
        proposals: Repository[TokenizationProposal] = InjectRepository(TokenizationProposal),
        disclosures: Repository[DisclosureDocument] = InjectRepository(DisclosureDocument),
        token_series: Repository[TokenSeries] = InjectRepository(TokenSeries),
        deployments: Repository[SmartContractDeployment] = InjectRepository(SmartContractDeployment),
        assets: Repository[Asset] = InjectRepository(Asset),
        issuers: Repository[Issuer] = InjectRepository(Issuer),
        audit_logs: Repository[AuditLog] = InjectRepository(AuditLog),
    ):
        self.storage = storage
        self.ds = data_source
        self.proposals = proposals
        self.disclosures = disclosures
        self.token_series = token_series
        self.deployments = deployments
        self.assets = assets
        self.issuers = issuers
        self.audit_logs = audit_logs

    # -- issuer-facing: proposal lifecycle ----------------------------------------------------

    async def create_proposal(self, user_id: int, dto: CreateProposalDto) -> ProposalDetailResponseDto:
        issuer = await self._get_issuer_by_user_or_raise(user_id)

        asset = await self.assets.find_one(FindOptions(where={"id": dto.asset_id}, relations=["issuer"]))
        if asset is None or asset.issuer is None or asset.issuer.id != issuer.id:
            raise NotFoundException(t("issuance.error.asset_not_found"))
        # ★ Tokenization-readiness gate -- see `TokenizationProposal`'s docstring for why this
        # single check at creation time is sufficient to keep `LAUNCHED` unreachable for a
        # non-tokenization-ready asset (custodian attachment is monotonic -- `AssetsService` has
        # no "detach" operation, `CustodiansService` has no "un-verify" operation).
        if not asset.custodian_verified:
            raise ConflictException(t("issuance.error.asset_not_tokenization_ready"))

        proposal = await self.proposals.save(
            # `# type: ignore[call-arg]` -- see the note on `User(...)` in `AuthService.register()`
            # (`austial-py` `py.typed` gap, tracked for `austial-framework-dev`).
            TokenizationProposal(  # type: ignore[call-arg]
                asset=asset,
                issuer=issuer,
                total_units=dto.total_units,
                unit_price_usd=dto.unit_price_usd,
                min_subscription_units=dto.min_subscription_units,
                subscription_start_at=dto.subscription_start_at,
                subscription_end_at=dto.subscription_end_at,
                status="DRAFT",
            )
        )
        await self._write_audit_log(
            entity_id=str(proposal.id),
            actor_user_id=user_id,
            action="issuance.proposal.created",
            before_state=None,
            after_state={"status": "DRAFT", "asset_id": asset.id},
        )
        return await self._to_detail_dto(await self._get_own_proposal_or_raise(proposal.id, user_id))

    async def list_my_proposals(self, user_id: int, *, skip: int, take: int) -> ProposalListDto:
        issuer = await self._get_issuer_by_user_or_raise(user_id)
        proposals, total = await (
            self.proposals.create_query_builder("p")
            .left_join_and_select("p.asset", "asset")
            .left_join_and_select("p.issuer", "issuer")
            .where("p.issuer_id = :issuer_id", {"issuer_id": issuer.id})
            .add_order_by("p.id", "DESC")
            .skip(skip)
            .take(take)
            .get_many_and_count()
        )
        return ProposalListDto(total=total, items=[_to_proposal_dto(p) for p in proposals])

    async def get_my_proposal(self, user_id: int, proposal_id: int) -> ProposalDetailResponseDto:
        proposal = await self._get_own_proposal_or_raise(proposal_id, user_id)
        return await self._to_detail_dto(proposal)

    async def submit_for_review(self, user_id: int, proposal_id: int) -> ProposalDetailResponseDto:
        """``DRAFT -> DOCUMENTATION_REVIEW``, issuer-initiated. All proposal fields are already
        required at ``CreateProposalDto`` validation time, so "requires proposal fields complete"
        (per the build plan) reduces to the transition-legality check alone -- there is no
        DRAFT-only optional field this step needs to additionally verify."""
        proposal = await self._get_own_proposal_or_raise(proposal_id, user_id)
        await self._transition(
            proposal, "DOCUMENTATION_REVIEW", actor_user_id=user_id, action="issuance.proposal.submitted_for_review"
        )
        return await self._to_detail_dto(proposal)

    # -- compliance-officer/admin-facing: pipeline + review -----------------------------------

    async def list_pipeline(self, *, status: str | None, skip: int, take: int) -> ProposalListDto:
        query = (
            self.proposals.create_query_builder("p")
            .left_join_and_select("p.asset", "asset")
            .left_join_and_select("p.issuer", "issuer")
        )
        if status:
            # `CAST(... AS TEXT)` -- see `kyc_service.py`'s equivalent workaround for why a plain
            # `p.status = :status` fails against real Postgres enum columns.
            query = query.where("CAST(p.status AS TEXT) = :status", {"status": status})
        proposals, total = await query.add_order_by("p.id", "ASC").skip(skip).take(take).get_many_and_count()
        return ProposalListDto(total=total, items=[_to_proposal_dto(p) for p in proposals])

    async def get_proposal(self, proposal_id: int) -> ProposalDetailResponseDto:
        proposal = await self._get_proposal_or_raise(proposal_id)
        return await self._to_detail_dto(proposal)

    async def compliance_approve(self, officer_id: int, proposal_id: int) -> ProposalDetailResponseDto:
        proposal = await self._get_proposal_or_raise(proposal_id)
        await self._transition(
            proposal,
            "COMPLIANCE_APPROVED",
            actor_user_id=officer_id,
            action="issuance.proposal.compliance_approved",
            extra_fields={"reviewed_by_user_id": officer_id},
        )
        return await self._to_detail_dto(proposal)

    async def reject(self, officer_id: int, proposal_id: int, dto: RejectProposalDto) -> ProposalDetailResponseDto:
        """Legal from either ``DOCUMENTATION_REVIEW`` (compliance rejection) or ``IFSCA_FILED``
        (regulator rejection recorded by the officer) -- both terminal, see ``ALLOWED_TRANSITIONS``."""
        proposal = await self._get_proposal_or_raise(proposal_id)
        await self._transition(
            proposal,
            "REJECTED",
            actor_user_id=officer_id,
            action="issuance.proposal.rejected",
            extra_fields={"reviewed_by_user_id": officer_id, "rejection_reason": dto.reason},
        )
        return await self._to_detail_dto(proposal)

    async def file_with_ifsca(self, officer_id: int, proposal_id: int, dto: FileIfscaDto) -> ProposalDetailResponseDto:
        proposal = await self._get_proposal_or_raise(proposal_id)
        await self._transition(
            proposal,
            "IFSCA_FILED",
            actor_user_id=officer_id,
            action="issuance.proposal.filed_with_ifsca",
            extra_fields={"reviewed_by_user_id": officer_id, "ifsca_filing_reference": dto.filing_reference},
        )
        return await self._to_detail_dto(proposal)

    async def ifsca_approve(self, officer_id: int, proposal_id: int, dto: IfscaApproveDto) -> ProposalDetailResponseDto:
        proposal = await self._get_proposal_or_raise(proposal_id)
        await self._transition(
            proposal,
            "IFSCA_APPROVED",
            actor_user_id=officer_id,
            action="issuance.proposal.ifsca_approved",
            extra_fields={"reviewed_by_user_id": officer_id, "ifsca_approval_reference": dto.approval_reference},
        )
        return await self._to_detail_dto(proposal)

    async def launch(self, officer_id: int, proposal_id: int, dto: LaunchProposalDto) -> TokenSeriesResponseDto:
        proposal = await self._get_proposal_or_raise(proposal_id)
        if proposal.status != "IFSCA_APPROVED":
            raise ConflictException(t("issuance.error.not_ifsca_approved"))

        # ★ Defense-in-depth re-check of the tokenization-readiness gate -- see
        # `TokenizationProposal`'s docstring on why `create_proposal`'s single check is already
        # sufficient today, and why this is here anyway.
        if not proposal.asset.custodian_verified:
            raise ConflictException(t("issuance.error.asset_not_tokenization_ready"))

        present = await self._present_disclosure_types(proposal_id)
        missing = set(REQUIRED_DISCLOSURES) - present
        if missing:
            raise UnprocessableEntityException(t("issuance.error.disclosures_incomplete"))

        existing_symbol = await self.token_series.find_one_by({"symbol": dto.symbol})
        if existing_symbol is not None:
            raise ConflictException(t("issuance.error.symbol_already_exists"))

        async def work(em: Any) -> TokenSeries:
            # Atomic: `TokenSeries` creation + the proposal's `LAUNCHED` flip happen in one
            # transaction -- either both land or neither does, per the build plan's own code
            # sketch. `total_supply` is a snapshot of `proposal.total_units` at this instant
            # (see `TokenSeries`'s docstring), not a live read through the relation later.
            series = await em.save(
                TokenSeries(  # type: ignore[call-arg]
                    proposal=proposal,
                    symbol=dto.symbol,
                    total_supply=proposal.total_units,
                    contract_address=dto.contract_address,
                    paused=False,
                    launched_by_user_id=officer_id,
                )
            )
            await em.update(TokenizationProposal, proposal.id, {"status": "LAUNCHED"})
            return series

        series = await self.ds.transaction(work)
        series.proposal = proposal  # `em.save()` returns the instance as constructed -- already set, kept explicit.

        await self._write_audit_log(
            entity_id=str(proposal.id),
            actor_user_id=officer_id,
            action="issuance.proposal.launched",
            before_state={"status": "IFSCA_APPROVED"},
            after_state={"status": "LAUNCHED", "token_series_id": series.id, "symbol": series.symbol},
        )
        return _to_series_dto(series)

    # -- disclosures (issuer-uploaded, own proposal only) --------------------------------------

    async def get_disclosure_upload_url(
        self, user_id: int, proposal_id: int, dto: DisclosureUploadUrlRequestDto
    ) -> DisclosureUploadUrlResponseDto:
        proposal = await self._get_own_proposal_or_raise(proposal_id, user_id)
        self._assert_not_terminal(proposal)

        object_key = f"issuance/{proposal.id}/{dto.disclosure_type.lower()}/{uuid.uuid4().hex}"
        upload_url = self.storage.generate_upload_url(object_key, content_type=dto.content_type)
        return DisclosureUploadUrlResponseDto(upload_url=upload_url, object_key=object_key)

    async def add_disclosure(
        self, user_id: int, proposal_id: int, dto: AddDisclosureDto
    ) -> DisclosureDocumentResponseDto:
        proposal = await self._get_own_proposal_or_raise(proposal_id, user_id)
        self._assert_not_terminal(proposal)

        existing_of_type = await self._list_disclosures_of_type(proposal.id, dto.disclosure_type)
        for existing in existing_of_type:
            if existing.is_current:
                # See `DisclosureDocument`'s docstring -- supersede, never mutate/delete.
                await self.disclosures.update({"id": existing.id}, {"is_current": False})
        next_version = max((d.version for d in existing_of_type), default=0) + 1

        document = await self.disclosures.save(
            DisclosureDocument(  # type: ignore[call-arg]
                proposal=proposal,
                disclosure_type=dto.disclosure_type,
                object_key=dto.object_key,
                version=next_version,
                is_current=True,
                uploaded_by_user_id=user_id,
            )
        )
        await self._write_audit_log(
            entity_id=str(proposal.id),
            actor_user_id=user_id,
            action="issuance.disclosure.uploaded",
            before_state=None,
            after_state={"disclosure_type": dto.disclosure_type, "version": next_version},
        )
        return _to_disclosure_dto(document)

    # -- token series (circuit breaker + smart contract deployment) ----------------------------

    async def get_token_series(self, series_id: int) -> TokenSeriesResponseDto:
        series = await self._get_series_or_raise(series_id)
        return _to_series_dto(series)

    async def pause_token_series(self, officer_id: int, series_id: int) -> TokenSeriesResponseDto:
        """The backend half of the circuit-breaker control -- see ``TokenSeries``'s docstring."""
        series = await self._get_series_or_raise(series_id)
        if series.paused:
            raise ConflictException(t("issuance.error.token_series_already_paused"))
        await self.token_series.update({"id": series.id}, {"paused": True})
        await self._write_audit_log(
            entity_id=str(series.id),
            actor_user_id=officer_id,
            action="issuance.token_series.paused",
            before_state={"paused": False},
            after_state={"paused": True},
            entity_type="TokenSeries",
        )
        series.paused = True
        return _to_series_dto(series)

    async def resume_token_series(self, officer_id: int, series_id: int) -> TokenSeriesResponseDto:
        series = await self._get_series_or_raise(series_id)
        if not series.paused:
            raise ConflictException(t("issuance.error.token_series_not_paused"))
        await self.token_series.update({"id": series.id}, {"paused": False})
        await self._write_audit_log(
            entity_id=str(series.id),
            actor_user_id=officer_id,
            action="issuance.token_series.resumed",
            before_state={"paused": True},
            after_state={"paused": False},
            entity_type="TokenSeries",
        )
        series.paused = False
        return _to_series_dto(series)

    async def record_smart_contract_deployment(
        self, officer_id: int, series_id: int, dto: RecordSmartContractDeploymentDto
    ) -> TokenSeriesResponseDto:
        series = await self._get_series_or_raise(series_id)
        deployment = await self.deployments.save(
            SmartContractDeployment(  # type: ignore[call-arg]
                bytecode_hash=dto.bytecode_hash,
                version=dto.version,
                audit_report_ref=dto.audit_report_ref,
                deployed_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        # `.save()`, not `.update()` -- setting a `ManyToOne` relation's FK column requires the
        # full-column path (`Repository.update()` cannot touch relation columns at all -- see the
        # identical note on `AssetsService.attach_custodian`). `series` was loaded with both
        # `proposal` and `smart_contract_deployment` eager-loaded by `_get_series_or_raise`
        # specifically so this `.save()` doesn't null out the unloaded `proposal` relation.
        series.smart_contract_deployment = deployment
        saved = await self.token_series.save(series)
        await self._write_audit_log(
            entity_id=str(series.id),
            actor_user_id=officer_id,
            action="issuance.token_series.smart_contract_deployment_recorded",
            before_state=None,
            after_state={"smart_contract_deployment_id": deployment.id},
            entity_type="TokenSeries",
        )
        return _to_series_dto(saved)

    # -- internals ----------------------------------------------------------------------------

    def _assert_transition(self, current_status: str, target_status: str) -> None:
        if target_status not in ALLOWED_TRANSITIONS.get(current_status, set()):
            raise ConflictException(
                t("issuance.error.invalid_transition").format(current=current_status, target=target_status)
            )

    def _assert_not_terminal(self, proposal: TokenizationProposal) -> None:
        if proposal.status in ("LAUNCHED", "REJECTED"):
            raise ConflictException(t("issuance.error.proposal_terminal"))

    async def _transition(
        self,
        proposal: TokenizationProposal,
        target_status: str,
        *,
        actor_user_id: int,
        action: str,
        extra_fields: dict[str, Any] | None = None,
    ) -> None:
        self._assert_transition(proposal.status, target_status)
        before_status = proposal.status
        update_fields = {"status": target_status, **(extra_fields or {})}
        await self.proposals.update({"id": proposal.id}, update_fields)
        proposal.status = target_status
        for key, value in (extra_fields or {}).items():
            setattr(proposal, key, value)
        await self._write_audit_log(
            entity_id=str(proposal.id),
            actor_user_id=actor_user_id,
            action=action,
            before_state={"status": before_status},
            after_state=update_fields,
        )

    async def _present_disclosure_types(self, proposal_id: int) -> set[str]:
        current = await self._list_current_disclosures(proposal_id)
        return {d.disclosure_type for d in current}

    async def _list_current_disclosures(self, proposal_id: int) -> list[DisclosureDocument]:
        return await (
            self.disclosures.create_query_builder("d")
            .where("d.proposal_id = :proposal_id", {"proposal_id": proposal_id})
            .and_where("d.is_current = :is_current", {"is_current": True})
            .add_order_by("d.disclosure_type", "ASC")
            .get_many()
        )

    async def _list_disclosures_of_type(self, proposal_id: int, disclosure_type: str) -> list[DisclosureDocument]:
        return await (
            self.disclosures.create_query_builder("d")
            .where("d.proposal_id = :proposal_id", {"proposal_id": proposal_id})
            # `CAST(... AS TEXT)` -- see `kyc_service.py`'s equivalent workaround.
            .and_where("CAST(d.disclosure_type AS TEXT) = :disclosure_type", {"disclosure_type": disclosure_type})
            .add_order_by("d.id", "ASC")
            .get_many()
        )

    async def _get_issuer_by_user_or_raise(self, user_id: int) -> Issuer:
        issuer = await (
            self.issuers.create_query_builder("issuer")
            .where("issuer.user_id = :user_id", {"user_id": user_id})
            .get_one()
        )
        if issuer is None:
            raise NotFoundException(t("issuance.error.issuer_profile_required"))
        return issuer

    async def _get_proposal_or_raise(self, proposal_id: int) -> TokenizationProposal:
        proposal = await self.proposals.find_one(FindOptions(where={"id": proposal_id}, relations=["asset", "issuer"]))
        if proposal is None:
            raise NotFoundException(t("issuance.error.proposal_not_found"))
        return proposal

    async def _get_own_proposal_or_raise(self, proposal_id: int, user_id: int) -> TokenizationProposal:
        issuer = await self._get_issuer_by_user_or_raise(user_id)
        proposal = await self._get_proposal_or_raise(proposal_id)
        if proposal.issuer.id != issuer.id:
            # A `NotFoundException`, not `ForbiddenException` -- mirrors `AssetsService.
            # _get_own_asset_or_raise`: don't leak the existence of another issuer's proposal.
            raise NotFoundException(t("issuance.error.proposal_not_found"))
        return proposal

    async def _get_series_or_raise(self, series_id: int) -> TokenSeries:
        series = await self.token_series.find_one(
            FindOptions(where={"id": series_id}, relations=["proposal", "smart_contract_deployment"])
        )
        if series is None:
            raise NotFoundException(t("issuance.error.token_series_not_found"))
        return series

    async def _to_detail_dto(self, proposal: TokenizationProposal) -> ProposalDetailResponseDto:
        current = await self._list_current_disclosures(proposal.id)
        present_types = {d.disclosure_type for d in current}
        missing = sorted(set(REQUIRED_DISCLOSURES) - present_types)
        base = _to_proposal_dto(proposal)
        return ProposalDetailResponseDto(
            **base.model_dump(),
            disclosures=[_to_disclosure_dto(d) for d in current],
            missing_disclosure_types=missing,
            disclosures_complete=not missing,
        )

    async def _write_audit_log(
        self,
        *,
        entity_id: str,
        actor_user_id: int | None,
        action: str,
        before_state: dict[str, Any] | None,
        after_state: dict[str, Any] | None,
        entity_type: str = "TokenizationProposal",
    ) -> None:
        # In addition to (not instead of) the generic `AuditInterceptor` row every mutating
        # request already produces -- see that class's docstring, and `KycService`'s/
        # `IssuersService`'s identical convention for regulator-sensitive before/after diffs.
        await self.audit_logs.save(
            AuditLog(  # type: ignore[call-arg]
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_state=before_state,
                after_state=after_state,
                ip_address=None,
            )
        )
