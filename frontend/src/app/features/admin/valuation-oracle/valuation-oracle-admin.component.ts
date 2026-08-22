import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule, NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';

import { I18nService } from '../../../core/i18n/i18n.service';
import { TPipe } from '../../../core/i18n/t.pipe';
import { SubmitValuationFeedRequest, ValuationFeedStatus } from '../../../core/valuation/valuation.models';
import { ValuationService } from '../../../core/valuation/valuation.service';

type LoadState = 'idle' | 'loading' | 'error' | 'loaded';

/**
 * `ValuationController` has no bulk-list-all-series endpoint reachable from here, only
 * per-series feed history (`GET /valuation/feeds/token-series/:series_id`) -- so this reuses
 * the codebase's established lookup-by-id pattern (`proposal-review.component.ts`'s
 * `tokenSeriesIdLookup`) instead of a nonexistent listing.
 */
@Component({
  selector: 'app-valuation-oracle-admin',
  standalone: true,
  imports: [
    CurrencyPipe,
    DatePipe,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTableModule,
    TPipe,
  ],
  templateUrl: './valuation-oracle-admin.component.html',
  styleUrl: './valuation-oracle-admin.component.scss',
})
export default class ValuationOracleAdminComponent {
  private readonly valuationService = inject(ValuationService);
  private readonly i18n = inject(I18nService);
  private readonly fb = inject(NonNullableFormBuilder);

  readonly seriesIdLookup = signal('');
  readonly statusFilter = signal<ValuationFeedStatus | ''>('');
  readonly feedsState = signal<LoadState>('idle');
  readonly loadedSeriesId = signal<number | null>(null);
  readonly feeds = this.valuationService.seriesFeeds;
  readonly currentNav = this.valuationService.currentNav;
  readonly feedColumns = ['reported_at', 'nav_per_unit', 'source', 'anomaly_score', 'status', 'actions'];

  readonly approvingId = signal<number | null>(null);

  readonly submitForm = this.fb.group({
    token_series_id: this.fb.control<number | null>(null, [Validators.required]),
    nav_per_unit: this.fb.control<number | null>(null, [Validators.required, Validators.min(0.00000001)]),
    source: this.fb.control('', [Validators.required]),
    reported_at: this.fb.control('', [Validators.required]),
  });
  readonly submitting = signal(false);
  readonly submitError = signal<string | null>(null);
  readonly submitSuccess = signal(false);

  loadFeeds(): void {
    const id = Number(this.seriesIdLookup());
    if (!id) {
      return;
    }
    this.feedsState.set('loading');
    const status = this.statusFilter() || undefined;
    Promise.all([this.valuationService.listFeedsForSeries(id, status), this.valuationService.fetchCurrentNav(id)])
      .then(() => {
        this.loadedSeriesId.set(id);
        this.feedsState.set('loaded');
      })
      .catch(() => this.feedsState.set('error'));
  }

  async approve(feedId: number): Promise<void> {
    if (this.approvingId()) {
      return;
    }
    this.approvingId.set(feedId);
    try {
      await this.valuationService.approveFeed(feedId);
    } finally {
      this.approvingId.set(null);
    }
  }

  async submitFeed(): Promise<void> {
    if (this.submitForm.invalid || this.submitting()) {
      this.submitForm.markAllAsTouched();
      return;
    }
    this.submitting.set(true);
    this.submitError.set(null);
    this.submitSuccess.set(false);
    try {
      const value = this.submitForm.getRawValue();
      const request: SubmitValuationFeedRequest = {
        token_series_id: value.token_series_id as number,
        nav_per_unit: value.nav_per_unit as number,
        source: value.source,
        reported_at: new Date(value.reported_at).toISOString(),
      };
      await this.valuationService.submitFeed(request);
      this.submitSuccess.set(true);
      this.submitForm.reset({ token_series_id: null, nav_per_unit: null, source: '', reported_at: '' });
      if (this.loadedSeriesId() === request.token_series_id) {
        this.loadFeeds();
      }
    } catch (error: any) {
      const message =
        error?.userMessage ||
        error?.error?.message ||
        this.i18n.t('valuation.admin.submit_error');
      this.submitError.set(message);
    } finally {
      this.submitting.set(false);
    }
  }
}
