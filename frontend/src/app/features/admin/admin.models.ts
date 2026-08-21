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
 * screen only *reads* these, the owning domain service (`core/custodian/`) is the source
 * of truth. `GET /custodians` is assumed to be a plain top-level (not `/admin`-nested)
 * module -- see the ★ CONTRACT ASSUMPTION header on `core/custodian/custodian.models.ts`.
 */
export type { Custodian } from '../../core/custodian/custodian.models';

/**
 * `GET /issuers` list-all-issuers shape, assumed to be exposed by the same `issuers`
 * module as the issuer's own `GET /issuers/profile` self-service endpoint (mirroring how
 * `GET /kyc/review-queue` lives on the `kyc` module alongside investor-facing endpoints,
 * rather than under a separate `/admin/*` prefix) when called by an
 * `ADMIN`/`COMPLIANCE_OFFICER` caller. There is no confirmed distinct issuer
 * approve/reject action in this version of the backend (the `issuers` module hasn't
 * shipped yet at all) -- the admin screen surfaces this list read-only and says so
 * explicitly (`admin.issuers.approval_note`) rather than inventing one. See the ★
 * CONTRACT ASSUMPTION header on `core/issuer/issuer.models.ts`.
 */
export type { IssuerProfile as AdminIssuerListItem } from '../../core/issuer/issuer.models';
