import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CurrencyPipe } from '@angular/common';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { I18nService } from '../../core/i18n/i18n.service';
import { TPipe } from '../../core/i18n/t.pipe';
import { LedgerService } from '../../core/ledger/ledger.service';
import { MarketplaceService } from '../../core/marketplace/marketplace.service';
import { SubscriptionsService } from '../../core/subscriptions/subscriptions.service';

type LoadState = 'loading' | 'error' | 'loaded';

/**
 * Phase 6 subscription flow -- "mandatory risk/fee acknowledgment checkboxes," matching
 * `CreateSubscriptionDto`'s `risk_disclosure_accepted`/`fee_disclosure_accepted`, both required
 * (not optional) and both must be checked before `submit()` calls `SubscriptionsService.create()`
 * -- see `canSubmit`.
 *
 * Also surfaces the investor's `LedgerAccount.available_balance` (`GET /ledger/account`)
 * alongside the computed subscription amount so the investor can see upfront whether they have
 * enough funds.
 *
 * `MarketplaceTokenSeries.id` (the `TokenSeries` id, looked up via `MarketplaceService.findById`)
 * is what's sent as `CreateSubscriptionRequest.token_series_id`.
 */
@Component({
  selector: 'app-asset-subscribe',
  standalone: true,
  imports: [
    CurrencyPipe,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    TPipe,
  ],
  templateUrl: './asset-subscribe.component.html',
  styleUrl: './asset-subscribe.component.scss',
})
export default class AssetSubscribeComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly marketplace = inject(MarketplaceService);
  private readonly ledger = inject(LedgerService);
  private readonly subscriptions = inject(SubscriptionsService);
  private readonly i18n = inject(I18nService);

  readonly state = signal<LoadState>('loading');
  readonly listing = computed(() => this.marketplace.findById(this.listingId));
  readonly account = this.ledger.account;

  readonly riskAcknowledged = signal(false);
  readonly feeAcknowledged = signal(false);
  readonly submitting = signal(false);
  readonly submitError = signal<string | null>(null);
  readonly result = this.subscriptions.current;

  readonly unitsForm = this.fb.group({
    units: this.fb.control<number | null>(null, [Validators.required, Validators.min(1)]),
  });

  readonly amountUsd = computed(() => {
    const listing = this.listing();
    const units = this.unitsForm.controls.units.value;
    if (!listing || !units) {
      return 0;
    }
    return units * listing.unit_price_usd;
  });

  readonly hasSufficientFunds = computed(() => {
    const account = this.account();
    if (!account) {
      return true;
    }
    return this.amountUsd() <= account.available_balance;
  });

  readonly canSubmit = computed(
    () =>
      this.unitsForm.valid &&
      this.riskAcknowledged() &&
      this.feeAcknowledged() &&
      this.hasSufficientFunds() &&
      this.amountUsd() > 0 &&
      !this.submitting(),
  );

  private get listingId(): number {
    return Number(this.route.snapshot.paramMap.get('id'));
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    Promise.all([this.marketplace.listListings(), this.ledger.fetchAccount()])
      .then(() => {
        const listing = this.listing();
        if (!listing) {
          this.state.set('error');
          return;
        }
        this.unitsForm.controls.units.setValidators([Validators.required, Validators.min(listing.min_subscription_units)]);
        this.unitsForm.controls.units.updateValueAndValidity();
        this.state.set('loaded');
      })
      .catch(() => this.state.set('error'));
  }

  async submit(): Promise<void> {
    const listing = this.listing();
    const units = this.unitsForm.controls.units.value;
    if (!this.canSubmit() || !listing || !units) {
      return;
    }

    this.submitting.set(true);
    this.submitError.set(null);
    try {
      await this.subscriptions.create({
        token_series_id: listing.id,
        units,
        risk_disclosure_accepted: this.riskAcknowledged(),
        fee_disclosure_accepted: this.feeAcknowledged(),
      });
      // Refresh the account so the newly locked funds show up in `available_balance`/
      // `locked_balance` immediately.
      await this.ledger.fetchAccount();
    } catch (error: any) {
      const message =
        error?.userMessage ||
        error?.error?.message ||
        this.i18n.t('marketplace.asset_subscribe.submit_error');
      this.submitError.set(message);
    } finally {
      this.submitting.set(false);
    }
  }
}
