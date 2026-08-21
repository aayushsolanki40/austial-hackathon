import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { RouterLink } from '@angular/router';

import { TPipe } from '../../../core/i18n/t.pipe';
import { TokenizationProposal } from '../../../core/issuance/issuance.models';
import { IssuanceService, PIPELINE_STATUS_COLUMNS } from '../../../core/issuance/issuance.service';
import { AdminStateComponent } from '../shared/admin-state.component';

type LoadState = 'loading' | 'error' | 'loaded';

/**
 * Compliance-officer/admin issuance pipeline -- "kanban by status" per the build plan's Phase
 * 4 section: every `TokenizationProposal` across every issuer, grouped into one column per
 * `ProposalStatus` (`REJECTED` as its own terminal bucket). No drag-and-drop -- per-card
 * action buttons appropriate to that card's current stage are the actual mechanism, matching
 * the plan's own framing ("kanban here just means grouped by status").
 *
 * `GET /issuance/proposals` (the list endpoint backing this board) returns the lighter
 * `ProposalResponseDto` -- no `disclosures`/`missing_disclosure_types`/`disclosures_complete`.
 * That means this board can't show a real disclosure-completeness badge or gate a launch
 * action per-card without an extra detail fetch per proposal; the `IFSCA_APPROVED` column
 * therefore just links through to the full detail review (`ProposalReviewComponent`, which
 * fetches `ProposalDetail` and does the actual launch) rather than faking a checklist here.
 *
 * Deeper per-proposal review (full state, disclosure checklist, circuit breaker) lives at
 * `admin/issuance-pipeline/:id` (`ProposalReviewComponent`) -- this board's cards link there,
 * but also expose the single most common action for their column inline (where that action
 * doesn't need the detail-only fields) so a reviewer working through a column doesn't have to
 * open every card.
 */
@Component({
  selector: 'app-issuance-pipeline',
  standalone: true,
  imports: [FormsModule, RouterLink, MatButtonModule, MatCardModule, MatFormFieldModule, MatInputModule, AdminStateComponent, TPipe],
  templateUrl: './issuance-pipeline.component.html',
  styleUrl: './issuance-pipeline.component.scss',
})
export default class IssuancePipelineComponent implements OnInit {
  private readonly issuanceService = inject(IssuanceService);

  readonly state = signal<LoadState>('loading');
  readonly columns = PIPELINE_STATUS_COLUMNS;
  readonly pipelineByStatus = this.issuanceService.pipelineByStatus;

  readonly actioningId = signal<number | null>(null);
  readonly rejectReasons = signal<Record<number, string>>({});
  readonly filingReferences = signal<Record<number, string>>({});
  readonly approvalReferences = signal<Record<number, string>>({});

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    this.issuanceService
      .listPipeline()
      .then(() => this.state.set('loaded'))
      .catch(() => this.state.set('error'));
  }

  reasonFor(proposalId: number): string {
    return this.rejectReasons()[proposalId] ?? '';
  }

  setReason(proposalId: number, reason: string): void {
    this.rejectReasons.update((reasons) => ({ ...reasons, [proposalId]: reason }));
  }

  filingReferenceFor(proposalId: number): string {
    return this.filingReferences()[proposalId] ?? '';
  }

  setFilingReference(proposalId: number, value: string): void {
    this.filingReferences.update((refs) => ({ ...refs, [proposalId]: value }));
  }

  approvalReferenceFor(proposalId: number): string {
    return this.approvalReferences()[proposalId] ?? '';
  }

  setApprovalReference(proposalId: number, value: string): void {
    this.approvalReferences.update((refs) => ({ ...refs, [proposalId]: value }));
  }

  async approve(proposal: TokenizationProposal): Promise<void> {
    await this.run(proposal.id, () => this.issuanceService.complianceApprove(proposal.id));
  }

  async reject(proposal: TokenizationProposal): Promise<void> {
    const reason = this.reasonFor(proposal.id).trim();
    if (!reason) {
      return;
    }
    await this.run(proposal.id, () => this.issuanceService.reject(proposal.id, reason));
  }

  async recordFiling(proposal: TokenizationProposal): Promise<void> {
    const reference = this.filingReferenceFor(proposal.id).trim();
    if (!reference) {
      return;
    }
    await this.run(proposal.id, () => this.issuanceService.fileIfsca(proposal.id, reference));
  }

  async recordApproval(proposal: TokenizationProposal): Promise<void> {
    const reference = this.approvalReferenceFor(proposal.id).trim();
    if (!reference) {
      return;
    }
    await this.run(proposal.id, () => this.issuanceService.ifscaApprove(proposal.id, reference));
  }

  private async run(proposalId: number, action: () => Promise<unknown>): Promise<void> {
    this.actioningId.set(proposalId);
    try {
      await action();
    } finally {
      this.actioningId.set(null);
    }
  }
}
