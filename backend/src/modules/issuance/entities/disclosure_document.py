"""``DisclosureDocument`` entity -- Phase 4.

★ The headline rule of this phase (``AUSTIAL_BUILD_PLAN.md``): ``TokenizationProposal.status``
cannot reach ``LAUNCHED`` unless all six disclosure types -- ``RISK``, ``FEE``, ``LIQUIDITY``,
``CUSTODY``, ``TAX``, ``PROSPECTUS`` -- exist and are *current* for that proposal. Enforced in
``IssuanceService.launch`` (see that method's docstring); this entity only carries the data shape
the gate reads.

**Versioning -- "latest-per-type-wins, old rows kept for audit trail" (deliberate choice, not the
only valid one)**: a disclosure can legitimately need re-uploading mid-pipeline (e.g. IFSCA
requests a revised risk disclosure between ``IFSCA_FILED`` and ``IFSCA_APPROVED``). Rather than
updating a document row in place (which would destroy the audit trail of what was actually shown
to regulators/investors at each point in time) or deleting the superseded row (ditto, plus this
codebase's broader "nothing regulator-relevant gets physically deleted" convention -- see
``AuditLog``/``ComplianceReport``'s append-only-adjacent posture elsewhere in the plan), a new
upload for an already-present ``disclosure_type`` **inserts a new row** and flips the previous
current row's ``is_current`` to ``False`` (``IssuanceService.add_disclosure`` does both, in that
order) -- superseded rows are never mutated again after that, and never deleted. ``version`` is a
strictly increasing per-``(proposal, disclosure_type)`` counter purely for human-readable
ordering/display; the completeness gate itself only ever looks at ``is_current``.

File storage: presigned S3 URLs via the same upload-url/confirm two-step pattern
``src/modules/kyc/``'s ``KycDocument`` already established (``KycService.
get_document_upload_url``/``add_document``) -- see ``IssuanceService``'s mirrored
``get_disclosure_upload_url``/``add_disclosure``. The file bytes themselves are never stored here
or proxied through the API process, only the S3 object key a presigned URL was issued for.
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, EnumType, ManyToOne, PrimaryGeneratedColumn

from src.modules.issuance.entities.tokenization_proposal import TokenizationProposal

DISCLOSURE_TYPES = ("RISK", "FEE", "LIQUIDITY", "CUSTODY", "TAX", "PROSPECTUS")


@Entity()
class DisclosureDocument:
    id: int = PrimaryGeneratedColumn()
    proposal: TokenizationProposal = ManyToOne(lambda: TokenizationProposal, inverse_side="disclosures", nullable=False)

    disclosure_type: str = Column(type_=EnumType(values=DISCLOSURE_TYPES))
    object_key: str = Column()

    # Per-`(proposal, disclosure_type)` counter, 1-based -- see this module's docstring on
    # versioning. Never decremented/reused, even across superseded rows.
    version: int = Column(default=1)
    # `True` for exactly the most recent upload of this `(proposal, disclosure_type)` pair at any
    # given time -- the completeness gate in `IssuanceService.launch` reads only rows where this
    # is `True`. Flipped to `False` on the previous row the moment a new one is added; never
    # flipped back.
    is_current: bool = Column(default=True)
    uploaded_by_user_id: int = Column(nullable=True)

    created_at: datetime = CreateDateColumn()
