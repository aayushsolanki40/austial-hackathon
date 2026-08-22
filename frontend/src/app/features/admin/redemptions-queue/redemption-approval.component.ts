import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule, NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';

import { I18nService } from '../../../core/i18n/i18n.service';
import { TPipe } from '../../../core/i18n/t.pipe';
import { CreateDistributionRequest, DistributionStatus, ProcessDistributionResult, RedemptionStatus } from '../../../core/redemptions/redemptions.models';
import { RedemptionsService } from '../../../core/redemptions/redemptions.service';
import { FormFieldComponent } from '../../../shared/components/form-field/form-field.component';
import { SelectComponent, type SelectOption } from '../../../shared/components/select/select.component';
import { TabsComponent } from '../../../shared/components/tabs/tabs.component';
import { TabComponent } from '../../../shared/components/tabs/tab.component';

type LoadState = 'loading' | 'error' | 'loaded';

/**
 * Ops queue (`COMPLIANCE_OFFICER`/`ADMIN`, per `admin.routes.ts`'s `roleGuard`) for the
 * `RedemptionRequest` state machine plus distributions -- folded into one page as two tabs
 * rather than a separate nav entry/route, since `admin-shell.component.ts`'s `NAV_LINKS` only
 * reserves one nav slot (`redemptions`) for this phase and distributions has no back-reference
 * from redemptions worth a dedicated screen.
 */
@Component({
  selector: 'app-redemption-approval',
  standalone: true,
  imports: [
    CurrencyPipe,
    DatePipe,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatTableModule,
    FormFieldComponent,
    SelectComponent,
    TabsComponent,
    TabComponent,
    TPipe,
  ],
  templateUrl: './redemption-approval.component.html',
  styleUrl: './redemption-approval.component.scss',
})
export default class RedemptionApprovalComponent implements OnInit {
  private readonly redemptionsService = inject(RedemptionsService);
  private readonly i18n = inject(I18nService);
  private readonly fb = inject(NonNullableFormBuilder);

  // -- queue tab -----------------------------------------------------------------------------

  readonly queueState = signal<LoadState>('loading');
  readonly statusFilter = signal<RedemptionStatus | ''>('');
  readonly queue = this.redemptionsService.queue;
  readonly statusFilterOptions: SelectOption[] = [
    { value: '', label: this.i18n.t('redemptions.admin.status_filter_all') },
    { value: 'REQUESTED', label: this.i18n.t('redemptions.status_option.requested') },
    { value: 'COMPLIANCE_APPROVED', label: this.i18n.t('redemptions.status_option.compliance_approved') },
    { value: 'CUSTODIAN_RELEASED', label: this.i18n.t('redemptions.status_option.custodian_released') },
    { value: 'COMPLETED', label: this.i18n.t('redemptions.status_option.completed') },
    { value: 'REJECTED', label: this.i18n.t('redemptions.status_option.rejected') },
    { value: 'CANCELLED', label: this.i18n.t('redemptions.status_option.cancelled') },
  ];
  readonly queueColumns = [
    'id',
    'investor_id',
    'symbol',
    'units_requested',
    'nav_snapshot',
    'payout_amount',
    'status',
    'created_at',
    'actions',
  ];
  readonly actioningId = signal<number | null>(null);
  readonly rejectReasons = signal<Record<number, string>>({});

  // -- distributions tab -----------------------------------------------------------------------

  readonly distributionsState = signal<LoadState>('loading');
  readonly distributionStatusFilter = signal<DistributionStatus | ''>('');
  readonly distributions = this.redemptionsService.distributions;
  readonly distributionStatusFilterOptions: SelectOption[] = [
    { value: '', label: this.i18n.t('redemptions.admin.status_filter_all') },
    { value: 'DRAFT', label: this.i18n.t('redemptions.distribution_status_option.draft') },
    { value: 'PROCESSING', label: this.i18n.t('redemptions.distribution_status_option.processing') },
    { value: 'COMPLETED', label: this.i18n.t('redemptions.distribution_status_option.completed') },
  ];
  readonly distributionColumns = ['id', 'token_series_id', 'total_amount', 'record_date', 'status', 'actions'];
  readonly processingId = signal<number | null>(null);
  readonly processResult = signal<ProcessDistributionResult | null>(null);
  readonly processError = signal<string | null>(null);

  readonly distributionForm = this.fb.group({
    token_series_id: this.fb.control<number | null>(null, [Validators.required]),
    total_amount: this.fb.control<number | null>(null, [Validators.required, Validators.min(0.01)]),
    currency: this.fb.control('USD'),
    record_date: this.fb.control('', [Validators.required]),
  });
  readonly creating = signal(false);
  readonly createError = signal<string | null>(null);

  ngOnInit(): void {
    this.loadQueue();
    this.loadDistributions();
  }

  // -- queue actions ---------------------------------------------------------------------------

  loadQueue(): void {
    this.queueState.set('loading');
    this.redemptionsService
      .listQueue(this.statusFilter() || undefined)
      .then(() => this.queueState.set('loaded'))
      .catch(() => this.queueState.set('error'));
  }

  reasonFor(id: number): string {
    return this.rejectReasons()[id] ?? '';
  }

  setReason(id: number, reason: string): void {
    this.rejectReasons.update((reasons) => ({ ...reasons, [id]: reason }));
  }

  async approve(id: number): Promise<void> {
    await this.runQueueAction(id, () => this.redemptionsService.approve(id));
  }

  async reject(id: number): Promise<void> {
    const reason = this.reasonFor(id).trim();
    if (!reason) {
      return;
    }
    await this.runQueueAction(id, () => this.redemptionsService.reject(id, reason));
  }

  async release(id: number): Promise<void> {
    await this.runQueueAction(id, () => this.redemptionsService.release(id));
  }

  async complete(id: number): Promise<void> {
    await this.runQueueAction(id, () => this.redemptionsService.complete(id));
  }

  private async runQueueAction(id: number, action: () => Promise<unknown>): Promise<void> {
    if (this.actioningId()) {
      return;
    }
    this.actioningId.set(id);
    try {
      await action();
    } finally {
      this.actioningId.set(null);
    }
  }

  // -- distributions actions --------------------------------------------------------------------

  loadDistributions(): void {
    this.distributionsState.set('loading');
    this.redemptionsService
      .listDistributions(this.distributionStatusFilter() || undefined)
      .then(() => this.distributionsState.set('loaded'))
      .catch(() => this.distributionsState.set('error'));
  }

  async createDistribution(): Promise<void> {
    if (this.distributionForm.invalid || this.creating()) {
      this.distributionForm.markAllAsTouched();
      return;
    }
    this.creating.set(true);
    this.createError.set(null);
    try {
      const value = this.distributionForm.getRawValue();
      const request: CreateDistributionRequest = {
        token_series_id: value.token_series_id as number,
        total_amount: value.total_amount as number,
        currency: value.currency,
        record_date: value.record_date,
      };
      await this.redemptionsService.createDistribution(request);
      this.distributionForm.reset({ token_series_id: null, total_amount: null, currency: 'USD', record_date: '' });
    } catch {
      this.createError.set(this.i18n.t('redemptions.admin.create_distribution_error'));
    } finally {
      this.creating.set(false);
    }
  }

  async processDistribution(id: number): Promise<void> {
    if (this.processingId()) {
      return;
    }
    this.processingId.set(id);
    this.processError.set(null);
    try {
      const result = await this.redemptionsService.processDistribution(id);
      this.processResult.set(result);
    } catch {
      this.processError.set(this.i18n.t('redemptions.admin.process_error'));
    } finally {
      this.processingId.set(null);
    }
  }
}
