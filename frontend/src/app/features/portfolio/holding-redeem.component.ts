import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { I18nService } from '../../core/i18n/i18n.service';
import { TPipe } from '../../core/i18n/t.pipe';
import { HoldingsService } from '../../core/holdings/holdings.service';
import { RedemptionsService } from '../../core/redemptions/redemptions.service';

type LoadState = 'loading' | 'error' | 'loaded';

@Component({
  selector: 'app-holding-redeem',
  standalone: true,
  imports: [
    CurrencyPipe,
    DatePipe,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatTableModule,
    TPipe,
  ],
  templateUrl: './holding-redeem.component.html',
  styleUrl: './holding-redeem.component.scss',
})
export default class HoldingRedeemComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly holdingsService = inject(HoldingsService);
  private readonly redemptionsService = inject(RedemptionsService);
  private readonly i18n = inject(I18nService);
  private readonly fb = inject(NonNullableFormBuilder);

  readonly state = signal<LoadState>('loading');
  readonly holding = this.holdingsService.current;

  readonly submitting = signal(false);
  readonly submitError = signal<string | null>(null);
  readonly result = signal<null | 'submitted'>(null);

  readonly requestsState = signal<LoadState>('loading');
  readonly cancellingId = signal<number | null>(null);
  readonly myRequestsForHolding = computed(() =>
    this.redemptionsService.myRedemptions().filter((r) => r.holding_id === this.holdingIdParam),
  );
  readonly requestColumns = ['created_at', 'units_requested', 'payout_amount', 'status', 'actions'];

  readonly holdingIdParam = Number(this.route.snapshot.paramMap.get('id'));

  readonly redeemForm = this.fb.group({
    units: this.fb.control<number | null>(null, [Validators.required, Validators.min(0.00000001)]),
  });

  readonly canSubmit = computed(() => {
    const holding = this.holding();
    const units = this.redeemForm.controls.units.value;
    return !!holding && holding.status === 'ACTIVE' && !!units && units > 0 && units <= holding.quantity && !this.submitting();
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    this.holdingsService
      .fetchMine(this.holdingIdParam)
      .then((holding) => {
        this.redeemForm.controls.units.setValidators([Validators.required, Validators.min(0.00000001), Validators.max(holding.quantity)]);
        this.redeemForm.controls.units.updateValueAndValidity();
        this.state.set('loaded');
      })
      .catch(() => this.state.set('error'));
    this.loadRequests();
  }

  loadRequests(): void {
    this.requestsState.set('loading');
    this.redemptionsService
      .listMine()
      .then(() => this.requestsState.set('loaded'))
      .catch(() => this.requestsState.set('error'));
  }

  async submit(): Promise<void> {
    if (!this.canSubmit()) {
      return;
    }
    const units = this.redeemForm.controls.units.value;
    if (!units) {
      return;
    }

    this.submitting.set(true);
    this.submitError.set(null);
    try {
      await this.redemptionsService.create({ holding_id: this.holdingIdParam, units_requested: units });
      this.result.set('submitted');
      this.redeemForm.reset({ units: null });
      await this.loadRequests();
    } catch (error: any) {
      const message =
        error?.userMessage ||
        error?.error?.message ||
        this.i18n.t('portfolio.holding_redeem.submit_error');
      this.submitError.set(message);
    } finally {
      this.submitting.set(false);
    }
  }

  async cancel(requestId: number): Promise<void> {
    if (this.cancellingId()) {
      return;
    }
    this.cancellingId.set(requestId);
    try {
      await this.redemptionsService.cancelMine(requestId);
    } finally {
      this.cancellingId.set(null);
    }
  }
}
