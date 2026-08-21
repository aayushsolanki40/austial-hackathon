import { DisclosureDocument } from '../issuance/issuance.models';
import { AssetClass } from '../issuer/issuer.models';

/**
 * ★ CONTRACT ASSUMPTION -- there is no confirmed investor-facing "browse launched assets"
 * endpoint today. `IssuanceService.listPipeline`/`fetchProposal` are
 * `@Roles("COMPLIANCE_OFFICER","ADMIN")`-gated and `listMyProposals`/`fetchMyProposal` are
 * `@Roles("ISSUER")`-gated, per `issuance.service.ts`'s own docstring -- neither is reachable
 * by an `INVESTOR`. Guessed a parallel, `@Roles("INVESTOR")`-gated `GET /issuance/marketplace`
 * route family, scoped server-side to `status = 'LAUNCHED'` proposals only (the sole
 * subscribable state per the Phase 6 state machine in the build plan). The shape below
 * flattens what an investor needs across `Asset` + `TokenizationProposal` + `TokenSeries` into
 * one read model rather than three round trips per listing -- reconcile field-by-field once
 * the real backend `subscriptions`/`holdings` work (and whatever it exposes for marketplace
 * browsing) lands.
 */
export interface MarketplaceListing {
  /** The owning `TokenizationProposal.id` -- what `/assets/:id` and `/assets/:id/subscribe`
   * route on, since a subscription is created against a proposal, not a raw asset id. */
  id: number;
  asset_id: number;
  asset_name: string;
  asset_class: AssetClass;
  asset_description: string | null;
  issuer_id: number;
  token_series_id: number | null;
  symbol: string | null;
  total_units: number;
  /** ★ CONTRACT ASSUMPTION -- units already subscribed/allocated, purely for a "N%
   * subscribed" indicator. Not present on any confirmed DTO today; defaults to `0` client-side
   * if the backend response omits it. */
  units_subscribed: number;
  unit_price_usd: number;
  min_subscription_units: number;
  subscription_start_at: string;
  subscription_end_at: string;
}

/** ★ CONTRACT ASSUMPTION -- single-listing detail, adding the disclosure documents needed for
 * the read-only prospectus viewer (reuses `DisclosureDocument` from the real Phase 4 contract;
 * only the envelope around it is guessed). */
export interface MarketplaceListingDetail extends MarketplaceListing {
  disclosures: DisclosureDocument[];
}

/** ★ CONTRACT ASSUMPTION -- envelope, mirroring the `{ total, items }` shape every other
 * paginated list endpoint in this backend uses (`ProposalListResponse`, `AssetListResponse`,
 * `LedgerEntryListResponse`, ...). */
export interface MarketplaceListResponse {
  total: number;
  items: MarketplaceListing[];
}
