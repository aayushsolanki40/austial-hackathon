import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiService } from '../api/api.service';
import { CurrentNav, SubmitValuationFeedRequest, ValuationFeed, ValuationFeedListResponse, ValuationFeedStatus } from './valuation.models';

const FEED_PAGE_SIZE = 50;

/**
 * Signal-based state + `ApiService` calls, mirroring `SubscriptionsService`/`HoldingsService`'s
 * established shape. Real routes (`valuation_controller.py`):
 *   - `POST /valuation/feeds` -- ops-only, submit a new NAV report for a series.
 *   - `POST /valuation/feeds/:id/approve` -- ops-only, override a `QUARANTINED` feed to `PUBLISHED`.
 *   - `GET /valuation/feeds/token-series/:series_id?status=&skip=&take=` -- any authenticated role.
 *   - `GET /valuation/feeds/:id` -- single lookup.
 *   - `GET /valuation/token-series/:series_id/current-nav` -- current NAV for a series, with
 *     fallback to launch unit price when no feed has published yet.
 *
 * There is no endpoint to list feeds across every series at once -- every feed query is scoped to
 * one `token_series_id` (see `ValuationController`). `seriesFeeds` therefore always holds the
 * feed history for whichever single series was last loaded, not a cross-series aggregate.
 */
@Injectable({ providedIn: 'root' })
export class ValuationService {
  private readonly api = inject(ApiService);

  private readonly seriesFeedsSignal = signal<ValuationFeed[]>([]);
  private readonly currentNavSignal = signal<CurrentNav | null>(null);
  private readonly loadingSignal = signal(false);

  readonly seriesFeeds = this.seriesFeedsSignal.asReadonly();
  readonly currentNav = this.currentNavSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();

  /** `GET /valuation/feeds/token-series/:series_id?status=&skip=&take=`. Unwraps
   * `{ total, items }`, ordered newest-`reported_at`-first server-side. */
  async listFeedsForSeries(seriesId: number, status?: ValuationFeedStatus): Promise<ValuationFeed[]> {
    this.loadingSignal.set(true);
    try {
      const response = await firstValueFrom(
        this.api.get<ValuationFeedListResponse>(`/valuation/feeds/token-series/${seriesId}`, {
          status,
          skip: 0,
          take: FEED_PAGE_SIZE,
        }),
      );
      this.seriesFeedsSignal.set(response.items);
      return response.items;
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /** `GET /valuation/token-series/:series_id/current-nav`. */
  async fetchCurrentNav(seriesId: number): Promise<CurrentNav> {
    const nav = await firstValueFrom(this.api.get<CurrentNav>(`/valuation/token-series/${seriesId}/current-nav`));
    this.currentNavSignal.set(nav);
    return nav;
  }

  /** `POST /valuation/feeds`. Prepends the new feed to `seriesFeeds` if it belongs to the
   * currently-loaded series. */
  async submitFeed(request: SubmitValuationFeedRequest): Promise<ValuationFeed> {
    const feed = await firstValueFrom(this.api.post<ValuationFeed>('/valuation/feeds', request));
    this.seriesFeedsSignal.update((feeds) => (feeds.some((f) => f.token_series_id === feed.token_series_id) ? [feed, ...feeds] : feeds));
    return feed;
  }

  /** `POST /valuation/feeds/:id/approve` -- overrides a `QUARANTINED` feed to `PUBLISHED`.
   * Patches the feed in place in `seriesFeeds` with the server's response. */
  async approveFeed(id: number): Promise<ValuationFeed> {
    const feed = await firstValueFrom(this.api.post<ValuationFeed>(`/valuation/feeds/${id}/approve`));
    this.seriesFeedsSignal.update((feeds) => feeds.map((f) => (f.id === id ? feed : f)));
    return feed;
  }
}
