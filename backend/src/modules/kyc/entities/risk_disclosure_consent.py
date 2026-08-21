"""``RiskDisclosureConsent`` entity -- Phase 2 follow-up.

One row per investor's acknowledgment of the risk-disclosure text shown
during onboarding (see ``AUSTIAL_BUILD_PLAN.md`` Section 3's login-flow
note: "login -> KYC status check -> (onboarding if incomplete) -> risk-
disclosure acknowledgment -> dashboard. Disclosure acknowledgment is a
persisted, timestamped record.") -- deliberately **not** a client-side
cookie/localStorage flag: the whole point of this table is that it survives
a new browser, a new device, or a regulator audit years later.

Scoped to a single ``KycSubmission`` (one row per submission, mirrors
``KycDocument``'s FK shape) rather than directly to ``InvestorProfile``,
because the thing being gated -- ``KycService.submit()`` -- already operates
per-submission, and a submission's ``investor`` is reachable via
``consent.submission.investor`` when needed (see ``KycService._to_consent_dto``
callers). A fresh KYC submission (e.g. after a ``REJECTED`` outcome) requires
a fresh consent row, which is the correct behaviour: the investor should be
shown -- and acknowledge -- the disclosure again for each new attempt, not
have an old acknowledgment silently carried forward.

``disclosure_version`` identifies exactly which disclosure copy was shown --
required so a future change to the disclosure text doesn't silently
reinterpret an old consent as having covered wording the investor never
actually saw. Free-text/version-tag string (e.g. ``"2026-08-21"`` or
``"v1"``), not an enum -- the set of valid versions changes independently of
this codebase (a content/legal change, not a schema change).

Create-once record: no update/delete path exists or should ever be added
here (``KycService.record_consent`` only ever calls
``Repository.save()`` to insert), which is why ``acknowledged_at`` uses
``CreateDateColumn()`` rather than ``UpdateDateColumn()``.
"""

from __future__ import annotations

from datetime import datetime

from austial.orm import Column, CreateDateColumn, Entity, ManyToOne, PrimaryGeneratedColumn

from src.modules.kyc.entities.kyc_submission import KycSubmission


@Entity()
class RiskDisclosureConsent:
    id: int = PrimaryGeneratedColumn()
    submission: KycSubmission = ManyToOne(lambda: KycSubmission, inverse_side="consents", nullable=False)

    disclosure_version: str = Column()

    # Same pattern as `AuditLog.ip_address` -- best-effort provenance, not a security control.
    ip_address: str = Column(nullable=True)

    acknowledged_at: datetime = CreateDateColumn()
