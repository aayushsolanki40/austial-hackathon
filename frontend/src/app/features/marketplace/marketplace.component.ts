import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
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
 * Phase 6 marketplace: browsable list of launched, subscribable assets with an asset-class
 * filter, per the build plan's exact wording. Uses the existing `ASSET_CLASS_OPTIONS` list
 * (already established for the issuer's own asset-creation form) rather than inventing a
 * second copy of the closed `AssetClass` set. See `core/marketplace/marketplace.models.ts` for
 * the ★ CONTRACT ASSUMPTION this list is built on.
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
  readonly listings = this.marketplace.listings;
  readonly state = signal<LoadState>('loading');
  readonly selectedAssetClass = signal<AssetClass | null>(null);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    this.marketplace
      .listListings(this.selectedAssetClass() ?? undefined)
      .then(() => this.state.set('loaded'))
      .catch(() => this.state.set('error'));
  }

  setAssetClassFilter(value: AssetClass | null): void {
    this.selectedAssetClass.set(value);
    this.load();
  }
}
