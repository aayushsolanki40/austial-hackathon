import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { RouterLink } from '@angular/router';

import { I18nService } from '../../../core/i18n/i18n.service';
import { TPipe } from '../../../core/i18n/t.pipe';
import { IssuerService } from '../../../core/issuer/issuer.service';
import { CreateProposalRequest } from '../../../core/issuance/issuance.models';
import { IssuanceService } from '../../../core/issuance/issuance.service';

/**
 * Issuer-facing proposal list + creation form -- Phase 4's "an issuer creates a
 * `TokenizationProposal` against one of their own `tokenization_ready` assets" (see the build
 * plan's Phase 4 section). A sibling area to `features/issuer/portal/` rather than a section
 * bolted onto it, so the portal stays scoped to profile + asset submission and this stays
 * scoped to the issuance workflow that follows.
 *
 * Only assets with `tokenization_ready: true` are selectable (custodian already attached and
 * verified) -- picking anything else would just 409/422 server-side per this repo's existing
 * gating convention (`AttachCustodianRequest`'s custodian-must-be-verified rule).
 */
@Component({
  selector: 'app-issuer-proposals',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTableModule,
    TPipe,
  ],
  templateUrl: './issuer-proposals.component.html',
  styleUrl: './issuer-proposals.component.scss',
})
export default class IssuerProposalsComponent implements OnInit {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly issuerService = inject(IssuerService);
  private readonly issuanceService = inject(IssuanceService);
  private readonly i18n = inject(I18nService);

  readonly loading = signal(true);
  readonly proposals = this.issuanceService.myProposals;
  readonly assets = this.issuerService.assets;
  readonly tokenizationReadyAssets = computed(() => this.assets().filter((asset) => asset.tokenization_ready));

  readonly proposalColumns = ['asset', 'status', 'total_units', 'unit_price_usd', 'created_at', 'actions'];

  readonly submitting = signal(false);
  readonly error = signal<string | null>(null);

  readonly proposalForm = this.fb.group({
    asset_id: this.fb.control<number | null>(null, [Validators.required]),
    total_units: this.fb.control<number | null>(null, [Validators.required, Validators.min(1)]),
    unit_price_usd: this.fb.control<number | null>(null, [Validators.required, Validators.min(0.01)]),
    min_subscription_units: this.fb.control<number | null>(null, [Validators.required, Validators.min(1)]),
    subscription_start_at: this.fb.control('', [Validators.required]),
    subscription_end_at: this.fb.control('', [Validators.required]),
  });

  async ngOnInit(): Promise<void> {
    this.loading.set(true);
    try {
      await Promise.all([this.issuerService.listAssets(), this.issuanceService.listMyProposals()]);
    } finally {
      this.loading.set(false);
    }
  }

  assetNameFor(assetId: number): string {
    return this.assets().find((asset) => asset.id === assetId)?.name ?? `#${assetId}`;
  }

  async submitProposal(): Promise<void> {
    if (this.proposalForm.invalid || this.submitting()) {
      this.proposalForm.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.error.set(null);
    try {
      const value = this.proposalForm.getRawValue();
      const request: CreateProposalRequest = {
        asset_id: value.asset_id as number,
        total_units: value.total_units as number,
        unit_price_usd: value.unit_price_usd as number,
        min_subscription_units: value.min_subscription_units as number,
        subscription_start_at: value.subscription_start_at,
        subscription_end_at: value.subscription_end_at,
      };
      await this.issuanceService.createProposal(request);
      this.proposalForm.reset({
        asset_id: null,
        total_units: null,
        unit_price_usd: null,
        min_subscription_units: null,
        subscription_start_at: '',
        subscription_end_at: '',
      });
    } catch {
      this.error.set(this.i18n.t('issuance.error.generic'));
    } finally {
      this.submitting.set(false);
    }
  }
}
