import { AssetClass } from '../issuer/issuer.models';

/**
 * `MarketplaceTokenSeriesDto` (real backend contract, `GET subscriptions/marketplace`) -- a
 * flat `TokenSeries` read model, already scoped server-side to launched/unpaused/currently
 * open-window series. There is no separate `GET /assets/:id` marketplace detail endpoint --
 * this is the only investor-facing marketplace shape the backend exposes, so the asset-detail
 * page reuses it rather than fetching a richer payload that doesn't exist.
 */
export interface MarketplaceTokenSeries {
  id: number;
  symbol: string;
  asset_id: number;
  asset_name: string;
  asset_class: AssetClass;
  issuer_id: number;
  total_supply: number;
  unit_price_usd: number;
  min_subscription_units: number;
  subscription_start_at: string;
  subscription_end_at: string;
}

export interface MarketplaceListResponse {
  total: number;
  items: MarketplaceTokenSeries[];
}
