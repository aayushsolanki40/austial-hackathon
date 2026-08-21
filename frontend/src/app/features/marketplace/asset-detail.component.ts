import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { TPipe } from '../../core/i18n/t.pipe';
import { MarketplaceService } from '../../core/marketplace/marketplace.service';
import { ValuationService } from '../../core/valuation/valuation.service';
import { NavChartComponent } from '../../shared/nav-chart/nav-chart.component';

type LoadState = 'loading' | 'error' | 'loaded';
type NavLoadState = 'loading' | 'error' | 'loaded';

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
  imports: [
    CurrencyPipe,
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatTableModule,
    RouterLink,
    NavChartComponent,
    TPipe,
  ],
  templateUrl: './asset-detail.component.html',
  styleUrl: './asset-detail.component.scss',
})
export default class AssetDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly marketplace = inject(MarketplaceService);
  private readonly valuation = inject(ValuationService);

  readonly state = signal<LoadState>('loading');
  readonly listing = computed(() => this.marketplace.findById(this.listingId));

  readonly navState = signal<NavLoadState>('loading');
  readonly currentNav = this.valuation.currentNav;
  readonly navHistory = this.valuation.seriesFeeds;
  readonly navHistoryColumns = ['reported_at', 'nav_per_unit', 'source'];

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
      .then(() => {
        const found = this.listing();
        this.state.set(found ? 'loaded' : 'error');
        if (found) {
          this.loadNav(found.id);
        }
      })
      .catch(() => this.state.set('error'));
  }

  private loadNav(seriesId: number): void {
    this.navState.set('loading');
    Promise.all([this.valuation.fetchCurrentNav(seriesId), this.valuation.listFeedsForSeries(seriesId)])
      .then(() => this.navState.set('loaded'))
      .catch(() => this.navState.set('error'));
  }
}
