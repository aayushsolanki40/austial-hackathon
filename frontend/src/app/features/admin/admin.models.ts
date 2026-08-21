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
