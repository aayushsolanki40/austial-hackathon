/** `RedemptionRequest.status` -- the exact `ALLOWED_TRANSITIONS` state machine from
 * `redemptions_service.py`:
 *   `REQUESTED -> COMPLIANCE_APPROVED -> CUSTODIAN_RELEASED -> COMPLETED`
 * branching from `REQUESTED` to `REJECTED` or `CANCELLED`. Every other status is terminal --
 * the frontend never re-derives or advances this itself, only reflects what the backend
 * returns. */
export type RedemptionStatus = 'REQUESTED' | 'COMPLIANCE_APPROVED' | 'CUSTODIAN_RELEASED' | 'COMPLETED' | 'REJECTED' | 'CANCELLED';

/** `POST /redemptions` request body -- `CreateRedemptionRequestDto`. Server-side validated
 * against `holding.status == 'ACTIVE'` and `units_requested <= holding.quantity`. */
export interface CreateRedemptionRequest {
  holding_id: number;
  units_requested: number;
}

/** `RedemptionRequestResponseDto`. `nav_per_unit_snapshot`/`payout_amount` are only populated
 * once compliance approves (`RedemptionsService.approve` snapshots the series' NAV at that
 * instant, not at request time or completion time). */
export interface RedemptionRequest {
  id: number;
  investor_id: number;
  holding_id: number;
  token_series_id: number;
  symbol: string;
  units_requested: number;
  nav_per_unit_snapshot: number | null;
  payout_amount: number | null;
  status: RedemptionStatus;
  rejection_reason: string | null;
  payout_instruction_id: number | null;
  processed_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface RedemptionRequestListResponse {
  total: number;
  items: RedemptionRequest[];
}

/** `POST /redemptions/:id/reject` request body -- `RejectRedemptionRequestDto`. */
export interface RejectRedemptionRequest {
  reason: string;
}

/** `Distribution.status`. `DRAFT -> PROCESSING -> COMPLETED`, all inside one atomic
 * `process_distribution` call -- there is no separate background-job step in this phase. */
export type DistributionStatus = 'DRAFT' | 'PROCESSING' | 'COMPLETED';

/** `POST /redemptions/distributions` request body -- `CreateDistributionDto`. `currency`
 * defaults to `"USD"` server-side if omitted. */
export interface CreateDistributionRequest {
  token_series_id: number;
  total_amount: number;
  currency?: string;
  record_date: string;
}

/** `DistributionResponseDto`. */
export interface Distribution {
  id: number;
  token_series_id: number;
  total_amount: number;
  currency: string;
  record_date: string;
  status: DistributionStatus;
  triggered_by_user_id: number | null;
  processed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DistributionListResponse {
  total: number;
  items: Distribution[];
}

/** `ProcessDistributionResultDto` -- the pro-rata payout batch result returned by
 * `POST /redemptions/distributions/:id/process`, run synchronously as an ops action button in
 * this phase (not a background job). */
export interface ProcessDistributionResult {
  distribution_id: number;
  token_series_id: number;
  total_amount: number;
  holder_count: number;
  total_credited: number;
}
