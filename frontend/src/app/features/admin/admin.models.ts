/**
 * Contract for `backend/src/modules/admin/` (Section 1.5 of
 * `AUSTIAL_BUILD_PLAN.md`). That backend module doesn't exist yet -- these
 * shapes are the frontend's fixed expectation of it, following the
 * snake_case convention every other backend DTO in this repo uses
 * (`UserResponseDto.created_at`, etc.). Update if the real endpoint ships
 * with a different shape.
 */

/** `GET /admin/dashboard/summary` response. */
export interface AdminDashboardSummary {
  aum_usd: number;
  investor_count: number;
  active_issuances: number;
  pending_kyc_count: number;
  open_aml_alert_count: number;
}

/** One row of `GET /admin/users`. */
export interface AdminUserSummary {
  id: number;
  email: string;
  role: string;
  status: string;
  created_at: string;
}

/**
 * The Compliance Officer KYC review queue is just the real `KycSubmission` shape --
 * re-exported here (rather than duplicated) so `features/admin/` doesn't need to import
 * across into `core/kyc/`'s directory for a type it only reads, mirroring how
 * `AdminDashboardSummary`/`AdminUserSummary` above are already admin-local types.
 * See `core/kyc/kyc.models.ts` for the full field-by-field docstring, and
 * `backend/src/modules/kyc/{kyc_controller.py,kyc_dto.py}` for the source of truth:
 *   - `GET /kyc/review-queue?skip=&take=` -> `{ total, items: KycSubmission[] }`
 *   - `POST /kyc/submissions/{id}/approve` -> flips the submission (and the investor's
 *     `InvestorProfile.kyc_status`) to `VERIFIED`
 *   - `POST /kyc/submissions/{id}/reject` with `{ reason: string }` -> flips both to
 *     `REJECTED` and stores `reason` as `review_notes`
 *
 * Note there is no `email`/`investor_type`/`jurisdiction` on this DTO -- those live on
 * the separate `InvestorProfile` resource, which the review queue endpoint doesn't join
 * against. The queue is keyed by `investor_id` (a numeric FK), not an email address.
 */
export type { KycSubmission as KycReviewQueueItem, KycSubmissionListResponse as KycReviewQueueResponse } from '../../core/kyc/kyc.models';

/**
 * Re-exported the same way as `KycReviewQueueItem` above, for the same reason: this admin
 * screen reads and mutates these through the owning domain service (`core/custodian/`),
 * which is the source of truth for the shape. `GET /custodians` is a plain top-level (not
 * `/admin`-nested) module, readable by both `COMPLIANCE_OFFICER` and `ISSUER` -- see
 * `core/custodian/custodian.models.ts`.
 */
export type { Custodian } from '../../core/custodian/custodian.models';

/**
 * `IssuerProfile` re-exported for the same reason as `Custodian` above: the admin issuer
 * review screen reads/mutates these via `GET /issuers/review-queue`, `POST
 * /issuers/:id/approve`, and `POST /issuers/:id/reject` (all `@Roles("COMPLIANCE_OFFICER")`,
 * confirmed against `backend/src/modules/issuers/issuers_controller.py`), the same real
 * `IssuersController` the issuer-portal's own-profile self-service endpoints live on. See
 * `core/issuer/issuer.models.ts` for the full field-by-field docstring.
 */
export type { IssuerProfile as AdminIssuerListItem, IssuerReviewQueueResponse } from '../../core/issuer/issuer.models';
