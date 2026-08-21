import { Component, OnInit, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTableModule } from '@angular/material/table';

import { ApiService } from '../../../core/api/api.service';
import { I18nService } from '../../../core/i18n/i18n.service';
import { TPipe } from '../../../core/i18n/t.pipe';
import { CustodianService } from '../../../core/custodian/custodian.service';
import { AdminIssuerListItem, IssuerReviewQueueResponse } from '../admin.models';
import { AdminStateComponent } from '../shared/admin-state.component';

type LoadState = 'loading' | 'error' | 'loaded';

const ISSUER_PAGE_SIZE = 50;

/**
 * Real Phase 3 admin screen, replacing the placeholder -- gated by the parent `/admin`
 * route's `roleGuard(['COMPLIANCE_OFFICER', 'ADMIN'])`, no additional per-route guard
 * needed here (matches `KycReviewQueueComponent`).
 *
 * Two sections, per Section 1.5's framing ("Phase 3's issuer approval + custodian
 * management"), both calling real backend endpoints:
 *
 *   1. **Custodians** -- `CustodianService`-backed: list, register a new custodian, and
 *      verify (the build plan's ★ gating rule: "an asset cannot be tokenized unless its
 *      custodian row is IFSCA-verified"). Verification is one-directional in this backend --
 *      there is no `POST /custodians/:id/unverify` endpoint, so there is no "unverify"
 *      affordance here (a possible future gap if IFSCA registrations can lapse).
 *   2. **Issuers** -- a genuine approval workflow against `IssuersController`'s
 *      compliance-facing routes (`backend/src/modules/issuers/issuers_controller.py`):
 *      `GET /issuers/review-queue?skip=&take=` -> `{ total, items }`, `POST
 *      /issuers/:id/approve`, `POST /issuers/:id/reject` with `{ reason }`. Called directly
 *      via `ApiService` (mirroring `KycReviewQueueComponent`'s pattern) rather than through
 *      `IssuerService`, which is scoped to the caller's own issuer profile, not this
 *      compliance-facing queue. The queue only ever contains `PENDING` issuers, so every row
 *      here is actionable; approved/rejected issuers drop out of it.
 */
@Component({
  selector: 'app-issuer-custodian-admin',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatFormFieldModule, MatInputModule, MatTableModule, AdminStateComponent, TPipe],
  templateUrl: './issuer-custodian-admin.component.html',
  styleUrl: './issuer-custodian-admin.component.scss',
})
export default class IssuerCustodianAdminComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly custodianService = inject(CustodianService);
  private readonly i18n = inject(I18nService);

  readonly custodians = this.custodianService.custodians;
  readonly custodianColumns = ['name', 'ifsca_registration_no', 'ifsca_verified', 'actions'];

  readonly custodianState = signal<LoadState>('loading');
  readonly verifyingId = signal<number | null>(null);
  readonly createSubmitting = signal(false);
  readonly createError = signal<string | null>(null);

  readonly issuerState = signal<LoadState>('loading');
  readonly issuerQueue = signal<AdminIssuerListItem[]>([]);
  readonly issuerColumns = ['legal_name', 'registration_number', 'registration_jurisdiction', 'verification_status', 'actions'];
  readonly rejectReasons = signal<Record<number, string>>({});
  readonly issuerActioningId = signal<number | null>(null);

  readonly createCustodianForm = this.fb.group({
    name: this.fb.control('', [Validators.required]),
    ifsca_registration_no: this.fb.control('', [Validators.required]),
  });

  ngOnInit(): void {
    this.loadCustodians();
    this.loadIssuerQueue();
  }

  loadCustodians(): void {
    this.custodianState.set('loading');
    this.custodianService
      .list()
      .then(() => this.custodianState.set('loaded'))
      .catch(() => this.custodianState.set('error'));
  }

  loadIssuerQueue(): void {
    this.issuerState.set('loading');
    this.api.get<IssuerReviewQueueResponse>('/issuers/review-queue', { skip: 0, take: ISSUER_PAGE_SIZE }).subscribe({
      next: (response) => {
        this.issuerQueue.set(response.items);
        this.issuerState.set('loaded');
      },
      error: () => this.issuerState.set('error'),
    });
  }

  async createCustodian(): Promise<void> {
    if (this.createCustodianForm.invalid || this.createSubmitting()) {
      this.createCustodianForm.markAllAsTouched();
      return;
    }

    this.createSubmitting.set(true);
    this.createError.set(null);
    try {
      await this.custodianService.create(this.createCustodianForm.getRawValue());
      this.createCustodianForm.reset({ name: '', ifsca_registration_no: '' });
    } catch {
      this.createError.set(this.i18n.t('custodian.error.generic'));
    } finally {
      this.createSubmitting.set(false);
    }
  }

  async verifyCustodian(id: number): Promise<void> {
    this.verifyingId.set(id);
    try {
      await this.custodianService.verify(id);
    } finally {
      this.verifyingId.set(null);
    }
  }

  reasonFor(issuerId: number): string {
    return this.rejectReasons()[issuerId] ?? '';
  }

  setReason(issuerId: number, reason: string): void {
    this.rejectReasons.update((reasons) => ({ ...reasons, [issuerId]: reason }));
  }

  approveIssuer(item: AdminIssuerListItem): void {
    this.issuerActioningId.set(item.id);
    this.api.post<AdminIssuerListItem>(`/issuers/${item.id}/approve`).subscribe({
      next: () => {
        this.issuerActioningId.set(null);
        this.removeFromQueue(item.id);
      },
      error: () => this.issuerActioningId.set(null),
    });
  }

  rejectIssuer(item: AdminIssuerListItem): void {
    const reason = this.reasonFor(item.id).trim();
    if (!reason) {
      return;
    }
    this.issuerActioningId.set(item.id);
    this.api.post<AdminIssuerListItem>(`/issuers/${item.id}/reject`, { reason }).subscribe({
      next: () => {
        this.issuerActioningId.set(null);
        this.removeFromQueue(item.id);
      },
      error: () => this.issuerActioningId.set(null),
    });
  }

  private removeFromQueue(issuerId: number): void {
    this.issuerQueue.update((items) => items.filter((item) => item.id !== issuerId));
  }
}
