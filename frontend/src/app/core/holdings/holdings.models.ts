/** `HoldingResponseDto`. A `Holding` is created once a `Subscription` reaches `ALLOCATED`.
 * No `asset_name`/`subscription_id` is denormalized onto this -- only `symbol` and
 * `token_series_id`. */
export type HoldingStatus = 'ACTIVE' | 'FROZEN' | 'REDEEMED';

export interface Holding {
  id: number;
  investor_id: number;
  token_series_id: number;
  symbol: string;
  quantity: number;
  avg_cost_usd: number;
  status: HoldingStatus;
  custodian_confirmation_ref: string | null;
  created_at: string;
  updated_at: string;
}

export interface HoldingListResponse {
  total: number;
  items: Holding[];
}
