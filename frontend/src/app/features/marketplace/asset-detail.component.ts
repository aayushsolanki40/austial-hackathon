import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { TPipe } from '../../core/i18n/t.pipe';
import { MarketplaceService } from '../../core/marketplace/marketplace.service';

type LoadState = 'loading' | 'error' | 'loaded';

/**
 * Phase 6 asset detail. `MarketplaceTokenSeriesDto` is the only investor-facing marketplace
 * contract the backend exposes -- there's no standalone detail endpoint -- so this loads the
 * same `GET subscriptions/marketplace` page `MarketplaceComponent` uses and looks the series up
 * by id client-side (`MarketplaceService.findById`).
 *
 * Known gap: investors have no read access to `issuance/proposals/:id` (that route is
 * `COMPLIANCE_OFFICER`/`ADMIN`/`ISSUER`-only), so there is currently no backend data source for
 * an investor-facing prospectus/disclosure viewer. Intentionally omitted here rather than wired
 * to a nonexistent endpoint.
 */
@Component({
  selector: 'app-asset-detail',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, MatButtonModule, MatCardModule, MatProgressSpinnerModule, RouterLink, TPipe],
  templateUrl: './asset-detail.component.html',
  styleUrl: './asset-detail.component.scss',
})
export default class AssetDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly marketplace = inject(MarketplaceService);

  readonly state = signal<LoadState>('loading');
  readonly listing = computed(() => this.marketplace.findById(this.listingId));

  readonly windowOpen = computed(() => {
    const listing = this.listing();
    if (!listing) {
      return false;
    }
    const now = Date.now();
    return now >= Date.parse(listing.subscription_start_at) && now <= Date.parse(listing.subscription_end_at);
  });

  private get listingId(): number {
    return Number(this.route.snapshot.paramMap.get('id'));
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    this.marketplace
      .listListings()
      .then(() => this.state.set(this.listing() ? 'loaded' : 'error'))
      .catch(() => this.state.set('error'));
  }
}
