import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiService } from '../api/api.service';
import { AssetClass } from '../issuer/issuer.models';
import { MarketplaceListing, MarketplaceListingDetail, MarketplaceListResponse } from './marketplace.models';

const LISTING_PAGE_SIZE = 50;

/**
 * ★ CONTRACT ASSUMPTION -- see `marketplace.models.ts` header; every route/shape below is a
 * guess, not a confirmed backend contract. Signal-based state + `ApiService` calls, mirroring
 * `IssuanceService`'s established shape. Guessed routes:
 *   - `GET /issuance/marketplace?asset_class=&skip=&take=` -- launched, subscribable listings,
 *     with an optional server-side asset-class filter (mirrors `listPipeline`'s optional
 *     `status` query-param convention).
 *   - `GET /issuance/marketplace/:id` -- single listing detail, including disclosures for the
 *     prospectus viewer.
 */
@Injectable({ providedIn: 'root' })
export class MarketplaceService {
  private readonly api = inject(ApiService);

  private readonly listingsSignal = signal<MarketplaceListing[]>([]);
  private readonly currentSignal = signal<MarketplaceListingDetail | null>(null);
  private readonly loadingSignal = signal(false);

  readonly listings = this.listingsSignal.asReadonly();
  readonly current = this.currentSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();

  /** `GET /issuance/marketplace?asset_class=&skip=&take=`. `assetClass` omitted entirely when
   * not filtering, rather than sent as an "ALL" sentinel value. */
  async listListings(assetClass?: AssetClass): Promise<MarketplaceListing[]> {
    this.loadingSignal.set(true);
    try {
      const response = await firstValueFrom(
        this.api.get<MarketplaceListResponse>('/issuance/marketplace', { asset_class: assetClass, skip: 0, take: LISTING_PAGE_SIZE }),
      );
      this.listingsSignal.set(response.items);
      return response.items;
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /** `GET /issuance/marketplace/:id`. Sets `current`. */
  async fetchListing(id: number): Promise<MarketplaceListingDetail> {
    const listing = await firstValueFrom(this.api.get<MarketplaceListingDetail>(`/issuance/marketplace/${id}`));
    this.currentSignal.set(listing);
    return listing;
  }
}
