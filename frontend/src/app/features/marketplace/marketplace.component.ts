import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { RouterLink } from '@angular/router';

import { ASSET_CLASS_OPTIONS } from '../../core/issuer/asset-class-fields';
import { AssetClass } from '../../core/issuer/issuer.models';
import { MarketplaceService } from '../../core/marketplace/marketplace.service';
import { TPipe } from '../../core/i18n/t.pipe';

type LoadState = 'loading' | 'error' | 'loaded';

/**
 * Phase 6 marketplace: browsable list of launched, subscribable assets (`GET
 * subscriptions/marketplace`) with an asset-class filter. The real endpoint only accepts
 * `skip`/`take` -- no server-side `asset_class` filter -- so the filter is applied client-side
 * over the single already-fetched page rather than re-requesting per filter change.
 */
@Component({
  selector: 'app-marketplace',
  standalone: true,
  imports: [
    CurrencyPipe,
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    RouterLink,
    TPipe,
  ],
  templateUrl: './marketplace.component.html',
  styleUrl: './marketplace.component.scss',
})
export default class MarketplaceComponent implements OnInit {
  private readonly marketplace = inject(MarketplaceService);

  readonly assetClassOptions = ASSET_CLASS_OPTIONS;
  readonly state = signal<LoadState>('loading');
  readonly selectedAssetClass = signal<AssetClass | null>(null);

  readonly listings = computed(() => {
    const filter = this.selectedAssetClass();
    const all = this.marketplace.listings();
    return filter ? all.filter((listing) => listing.asset_class === filter) : all;
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    this.marketplace
      .listListings()
      .then(() => this.state.set('loaded'))
      .catch(() => this.state.set('error'));
  }

  setAssetClassFilter(value: AssetClass | null): void {
    this.selectedAssetClass.set(value);
  }
}
