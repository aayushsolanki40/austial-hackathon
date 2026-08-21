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
import { AdminIssuerListItem } from '../admin.models';
import { AdminStateComponent } from '../shared/admin-state.component';

type LoadState = 'loading' | 'error' | 'loaded';

/**
 * Real Phase 3 admin screen, replacing the placeholder -- gated by the parent `/admin`
 * route's `roleGuard(['COMPLIANCE_OFFICER', 'ADMIN'])`, no additional per-route guard
 * needed here (matches `KycReviewQueueComponent`).
 *
 * Two sections, per Section 1.5's framing ("Phase 3's issuer approval + custodian
 * management"):
 *
 *   1. **Custodians** -- `CustodianService`-backed: list, register a new custodian, and
 *      flip `ifsca_verified` (the build plan's ★ gating rule: "an asset cannot be
 *      tokenized unless its custodian row is IFSCA-verified"). Fully wired, mutation and
 *      all.
 *   2. **Issuers** -- read-only list (`GET /issuers`, called directly via `ApiService`
 *      rather than through `IssuerService` since that service is scoped to the caller's
 *      *own* issuer profile, not an admin-facing list). There is no confirmed distinct
 *      issuer approve/reject action in this version of the backend -- the `issuers`
 *      module hasn't shipped at all yet, so rather than invent one, this section is
 *      explicitly read-only with an in-app note (`admin.issuers.approval_note`) saying so.
 *      Revisit once the real backend confirms whether such an action exists.
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
  readonly custodianColumns = ['name', 'ifsca_registration_no', 'jurisdiction', 'ifsca_verified', 'actions'];

  readonly custodianState = signal<LoadState>('loading');
  readonly verifyingId = signal<number | null>(null);
  readonly createSubmitting = signal(false);
  readonly createError = signal<string | null>(null);

  readonly issuerState = signal<LoadState>('loading');
  readonly issuers = signal<AdminIssuerListItem[]>([]);
  readonly issuerColumns = ['legal_name', 'registration_number', 'jurisdiction', 'verification_status'];

  readonly createCustodianForm = this.fb.group({
    name: this.fb.control('', [Validators.required]),
    ifsca_registration_no: this.fb.control('', [Validators.required]),
    jurisdiction: this.fb.control('', [Validators.required]),
  });

  ngOnInit(): void {
    this.loadCustodians();
    this.loadIssuers();
  }

  loadCustodians(): void {
    this.custodianState.set('loading');
    this.custodianService
      .list()
      .then(() => this.custodianState.set('loaded'))
      .catch(() => this.custodianState.set('error'));
  }

  loadIssuers(): void {
    this.issuerState.set('loading');
    this.api.get<AdminIssuerListItem[]>('/issuers').subscribe({
      next: (issuers) => {
        this.issuers.set(issuers);
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
      this.createCustodianForm.reset({ name: '', ifsca_registration_no: '', jurisdiction: '' });
    } catch {
      this.createError.set(this.i18n.t('custodian.error.generic'));
    } finally {
      this.createSubmitting.set(false);
    }
  }

  async toggleVerification(id: number, currentlyVerified: boolean): Promise<void> {
    this.verifyingId.set(id);
    try {
      if (currentlyVerified) {
        await this.custodianService.unverify(id);
      } else {
        await this.custodianService.verify(id);
      }
    } finally {
      this.verifyingId.set(null);
    }
  }
}
