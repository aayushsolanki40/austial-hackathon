import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { TPipe } from '../../../core/i18n/t.pipe';
import { ProposalStatus } from '../../../core/issuance/issuance.models';
import { IssuanceService } from '../../../core/issuance/issuance.service';
import { DisclosureChecklistComponent } from '../../../shared/disclosure-checklist/disclosure-checklist.component';

type LoadState = 'loading' | 'error' | 'loaded';

/** Statuses in which the issuer can still add/replace disclosure documents. Once a proposal
 * is `LAUNCHED` or `REJECTED` there's nothing left to disclose (launched -- already gated
 * complete at launch time; rejected -- terminal). */
const DISCLOSURE_EDITABLE_STATUSES: ProposalStatus[] = [
  'DRAFT',
  'DOCUMENTATION_REVIEW',
  'COMPLIANCE_APPROVED',
  'IFSCA_FILED',
  'IFSCA_APPROVED',
];

/**
 * Issuer's own view of a single `TokenizationProposal`: full state, the disclosure
 * completeness checklist (uploadable while the proposal is still moving through review), and
 * the one issuer-facing action available on it -- submit-for-review from `DRAFT`. Every other
 * transition (approve/reject/record-filing/record-approval/launch) is Compliance-Officer-only,
 * handled instead in `features/admin/issuance-pipeline/proposal-review.component.ts`.
 *
 * No token-series section here even once `LAUNCHED`: `GET /issuance/token-series/:id` is
 * `@Roles("COMPLIANCE_OFFICER", "ADMIN")`-gated, unreachable for the `ISSUER` role this
 * component serves.
 */
@Component({
  selector: 'app-issuer-proposal-detail',
  standalone: true,
  imports: [MatButtonModule, MatCardModule, MatProgressSpinnerModule, RouterLink, DisclosureChecklistComponent, TPipe],
  templateUrl: './proposal-detail.component.html',
  styleUrl: './proposal-detail.component.scss',
})
export default class ProposalDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly issuanceService = inject(IssuanceService);

  readonly state = signal<LoadState>('loading');
  readonly proposal = this.issuanceService.current;
  readonly submitting = signal(false);

  readonly canSubmitForReview = computed(() => this.proposal()?.status === 'DRAFT');
  readonly disclosuresEditable = computed(() => {
    const status = this.proposal()?.status;
    return status !== undefined && DISCLOSURE_EDITABLE_STATUSES.includes(status);
  });

  private get proposalId(): number {
    return Number(this.route.snapshot.paramMap.get('id'));
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    this.issuanceService
      .fetchMyProposal(this.proposalId)
      .then(() => this.state.set('loaded'))
      .catch(() => this.state.set('error'));
  }

  async submitForReview(): Promise<void> {
    this.submitting.set(true);
    try {
      await this.issuanceService.submitForReview(this.proposalId);
    } finally {
      this.submitting.set(false);
    }
  }

  onDisclosureUploaded(): void {
    this.load();
  }
}
