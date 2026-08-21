import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiService } from '../api/api.service';
import { MarketplaceListResponse, MarketplaceTokenSeries } from './marketplace.models';

const LISTING_PAGE_SIZE = 50;

/**
 * `GET subscriptions/marketplace?skip=&take=` -- the real controller only accepts `skip`/`take`,
 * no server-side `asset_class` filter, so `MarketplaceComponent` filters `listings()`
 * client-side instead of re-requesting. There is also no standalone detail endpoint, so
 * `findById` looks a series up in whatever `listListings()` already loaded rather than a second
 * round trip -- see `marketplace.models.ts` header.
 */
@Injectable({ providedIn: 'root' })
export class MarketplaceService {
  private readonly api = inject(ApiService);

  private readonly listingsSignal = signal<MarketplaceTokenSeries[]>([]);
  private readonly loadingSignal = signal(false);

  readonly listings = this.listingsSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();

  async listListings(): Promise<MarketplaceTokenSeries[]> {
    this.loadingSignal.set(true);
    try {
      const response = await firstValueFrom(
        this.api.get<MarketplaceListResponse>('/subscriptions/marketplace', { skip: 0, take: LISTING_PAGE_SIZE }),
      );
      this.listingsSignal.set(response.items);
      return response.items;
    } finally {
      this.loadingSignal.set(false);
    }
  }

  findById(id: number): MarketplaceTokenSeries | undefined {
    return this.listingsSignal().find((listing) => listing.id === id);
  }
}
