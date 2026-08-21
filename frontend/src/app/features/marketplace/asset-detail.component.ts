import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { TPipe } from '../../core/i18n/t.pipe';
import { MarketplaceService } from '../../core/marketplace/marketplace.service';
import { DisclosureChecklistComponent } from '../../shared/disclosure-checklist/disclosure-checklist.component';

type LoadState = 'loading' | 'error' | 'loaded';

/**
 * Phase 6 asset detail + prospectus viewer. Reuses `DisclosureChecklistComponent` in
 * read-only mode (`uploadable = false`) for the prospectus/disclosure section, the same
 * component the issuer/compliance screens use for the write side (Phase 4) -- see that
 * component's own docstring for why it lives under `shared/` for exactly this reason.
 *
 * `disclosures_complete`/`missing_disclosure_types` aren't part of the guessed
 * `MarketplaceListingDetail` shape (only `LAUNCHED` proposals -- already gated complete at
 * launch time -- ever reach the marketplace), so this passes `disclosuresComplete = true` and
 * an empty missing-types list rather than re-deriving completeness client-side.
 */
@Component({
  selector: 'app-asset-detail',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, MatButtonModule, MatCardModule, MatProgressSpinnerModule, RouterLink, DisclosureChecklistComponent, TPipe],
  templateUrl: './asset-detail.component.html',
  styleUrl: './asset-detail.component.scss',
})
export default class AssetDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly marketplace = inject(MarketplaceService);

  readonly state = signal<LoadState>('loading');
  readonly listing = this.marketplace.current;

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
      .fetchListing(this.listingId)
      .then(() => this.state.set('loaded'))
      .catch(() => this.state.set('error'));
  }
}
