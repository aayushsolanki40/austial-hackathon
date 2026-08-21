/**
 * ★ CONTRACT ASSUMPTION -- Phase 6's `holdings` backend module is being built in parallel by
 * `austial-backend-dev` and its real DTO shapes are not yet known to this frontend. Shape
 * guessed to mirror `Subscription`/`TokenSeries`; reconcile field-by-field once
 * `backend/src/modules/holdings/` exists.
 */

/** ★ CONTRACT ASSUMPTION -- `TokenHoldingResponseDto`, guessed. A `TokenHolding` is created
 * once a `Subscription` reaches `ALLOCATED` per the Phase 6 state machine in the build plan --
 * `subscription_id` is kept as the traceable link back to the originating subscription.
 * `asset_name`/`symbol` assumed denormalized for the same reason as on `Subscription`. */
export interface Holding {
  id: number;
  investor_id: number;
  subscription_id: number;
  token_series_id: number;
  asset_name: string;
  symbol: string | null;
  units: number;
  created_at: string;
}

/** ★ CONTRACT ASSUMPTION -- envelope, mirroring every other paginated list endpoint. */
export interface HoldingListResponse {
  total: number;
  items: Holding[];
}
