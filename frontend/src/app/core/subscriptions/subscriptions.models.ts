/**
 * ★ CONTRACT ASSUMPTION -- Phase 6's `subscriptions` backend module is being built in
 * parallel by `austial-backend-dev` and its real DTO shapes are not yet known to this
 * frontend. Everything in this file is a best-effort guess at a plausible contract, following
 * this repo's existing conventions (`{ total, items }` list envelope, an investor-scoped
 * `/mine` route family, `POST /:id/<action>` for state transitions) -- reconcile field-by-field
 * once `backend/src/modules/subscriptions/` exists.
 */

/** The Phase 6 state machine verbatim from the build plan:
 * `PENDING -> FUNDED -> CONFIRMED -> ALLOCATED`, branching to `REFUNDED`/`CANCELLED`. The
 * frontend never re-derives or advances this itself -- it only reflects whatever status the
 * backend returns. */
export type SubscriptionStatus = 'PENDING' | 'FUNDED' | 'CONFIRMED' | 'ALLOCATED' | 'REFUNDED' | 'CANCELLED';

/** ★ CONTRACT ASSUMPTION -- `POST /subscriptions` request body. `proposal_id` identifies which
 * `MarketplaceListing`/`TokenizationProposal` this subscribes into. `risk_acknowledged`/
 * `fee_acknowledged` record the two mandatory Phase 6 consent checkboxes the build plan calls
 * out explicitly; guessed as plain booleans the backend stores alongside a server-stamped
 * timestamp (mirrors the Phase 2 `RiskDisclosureStepComponent` pattern of a persisted,
 * timestamped acknowledgment record, not a client-side-only UI gate). Both must be `true` for
 * the request to be sent at all -- enforced client-side in `AssetSubscribeComponent` before
 * this type is ever constructed. */
export interface CreateSubscriptionRequest {
  proposal_id: number;
  units_requested: number;
  risk_acknowledged: boolean;
  fee_acknowledged: boolean;
}

/** ★ CONTRACT ASSUMPTION -- `SubscriptionResponseDto`, guessed. `amount_usd` is assumed
 * server-computed (`units_requested * unit_price_usd` at subscribe time) rather than
 * client-sent, mirroring how every other derived value in this backend
 * (`tokenization_ready`, `disclosures_complete`, `balance_after`, ...) is server-computed, never
 * trusted from the client. `asset_name`/`symbol` are assumed denormalized onto the response so
 * the portfolio list doesn't need a second lookup per row. */
export interface Subscription {
  id: number;
  investor_id: number;
  proposal_id: number;
  asset_name: string;
  symbol: string | null;
  units_requested: number;
  amount_usd: number;
  status: SubscriptionStatus;
  created_at: string;
  updated_at: string;
}

/** ★ CONTRACT ASSUMPTION -- envelope, mirroring `ProposalListResponse`/`AssetListResponse`. */
export interface SubscriptionListResponse {
  total: number;
  items: Subscription[];
}
