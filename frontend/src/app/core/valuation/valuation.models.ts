/** `ValuationFeed.status`. A feed deviating beyond the trailing-average anomaly threshold is
 * quarantined rather than published (`ValuationService.submit_feed`) -- an ops officer then
 * either leaves it quarantined or overrides via `approve_quarantined_feed`. */
export type ValuationFeedStatus = 'PUBLISHED' | 'QUARANTINED';

/** `POST /valuation/feeds` request body -- `SubmitValuationFeedDto`. `reported_at` is an ISO
 * datetime string, distinct from `created_at` (when the row was written). */
export interface SubmitValuationFeedRequest {
  token_series_id: number;
  nav_per_unit: number;
  source: string;
  reported_at: string;
}

/** `ValuationFeedResponseDto`. `anomaly_score` is `null` for a series' very first feed (no
 * trailing history to compare against). `reviewed_by_user_id`/`reviewed_at` are only set once a
 * quarantined feed has been overridden via `approve`. */
export interface ValuationFeed {
  id: number;
  token_series_id: number;
  nav_per_unit: number;
  source: string;
  anomaly_score: number | null;
  status: ValuationFeedStatus;
  reported_at: string;
  reviewed_by_user_id: number | null;
  reviewed_at: string | null;
  created_at: string;
}

/** `ValuationFeedListDto` -- envelope for `GET /valuation/feeds/token-series/:series_id`. */
export interface ValuationFeedListResponse {
  total: number;
  items: ValuationFeed[];
}

/** `CurrentNavResponseDto` -- `GET /valuation/token-series/:series_id/current-nav`. Falls back to
 * the series' launch unit price (`source: "PROPOSAL_UNIT_PRICE"`, `as_of: null`) when no
 * `PUBLISHED` feed exists yet for the series. */
export interface CurrentNav {
  token_series_id: number;
  nav_per_unit: number;
  source: string;
  as_of: string | null;
}
