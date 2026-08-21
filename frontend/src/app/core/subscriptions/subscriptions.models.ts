/** The Phase 6 state machine verbatim from the real backend:
 * `PENDING -> FUNDED -> CONFIRMED -> ALLOCATED`, branching to `REFUNDED`/`CANCELLED`. The
 * frontend never re-derives or advances this itself -- it only reflects whatever status the
 * backend returns. */
export type SubscriptionStatus = 'PENDING' | 'FUNDED' | 'CONFIRMED' | 'ALLOCATED' | 'REFUNDED' | 'CANCELLED';

/** `POST subscriptions` body (`CreateSubscriptionDto`). Both disclosure booleans are mandatory
 * (not optional) -- must be explicitly `true`, enforced client-side in `AssetSubscribeComponent`
 * before this type is ever constructed. */
export interface CreateSubscriptionRequest {
  token_series_id: number;
  units: number;
  risk_disclosure_accepted: boolean;
  fee_disclosure_accepted: boolean;
}

/** `SubscriptionResponseDto`. No `asset_name` is denormalized onto this -- only `symbol` -- so
 * list views identify a subscription by symbol, not asset name. */
export interface Subscription {
  id: number;
  investor_id: number;
  token_series_id: number;
  symbol: string;
  units: number;
  amount_usd: number;
  allocated_units: number | null;
  status: SubscriptionStatus;
  risk_disclosure_accepted: boolean;
  fee_disclosure_accepted: boolean;
  disclosures_acknowledged_at: string | null;
  processed_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionListResponse {
  total: number;
  items: Subscription[];
}
