import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { TPipe } from '../../../core/i18n/t.pipe';
import { IssuanceService } from '../../../core/issuance/issuance.service';
import { DisclosureChecklistComponent } from '../../../shared/disclosure-checklist/disclosure-checklist.component';

type LoadState = 'loading' | 'error' | 'loaded';

/**
 * Compliance-officer/admin review screen for a single `TokenizationProposal` -- full state,
 * the read-only disclosure completeness checklist (rendered straight from the server-computed
 * `missing_disclosure_types`/`disclosures_complete` on `ProposalDetail`), and every gated
 * action available for the proposal's *current* stage (approve/reject at
 * `DOCUMENTATION_REVIEW`, record-filed at `COMPLIANCE_APPROVED`, record-approved (or reject)
 * at `IFSCA_FILED`, launch at `IFSCA_APPROVED` once disclosures are complete), plus the
 * circuit-breaker pause/resume toggle and optional smart-contract-deployment recording form on
 * a `LAUNCHED` proposal's `TokenSeries`.
 *
 * `TokenSeries` is a standalone resource with no back-reference on `ProposalDetail` (see
 * `IssuanceService`'s header comment) -- `tokenSeries()` is populated automatically by a
 * `launch()` call made this session, or via the manual "load by id" lookup below for revisiting
 * an already-launched proposal in a fresh session.
 */
@Component({
  selector: 'app-proposal-review',
  standalone: true,
  imports: [FormsModule, RouterLink, DisclosureChecklistComponent, TPipe],
  templateUrl: './proposal-review.component.html',
  styleUrl: './proposal-review.component.scss',
})
export default class ProposalReviewComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly issuanceService = inject(IssuanceService);

  readonly state = signal<LoadState>('loading');
  readonly proposal = this.issuanceService.current;
  readonly tokenSeries = this.issuanceService.currentTokenSeries;
  readonly actioning = signal(false);
  readonly togglingCircuitBreaker = signal(false);
  readonly recordingDeployment = signal(false);
  readonly loadingTokenSeries = signal(false);

  readonly rejectReason = signal('');
  readonly filingReference = signal('');
  readonly approvalReference = signal('');
  readonly launchSymbol = signal('');
  readonly launchContractAddress = signal('');
  readonly tokenSeriesIdLookup = signal('');

  readonly deploymentBytecodeHash = signal('');
  readonly deploymentVersion = signal('');
  readonly deploymentAuditRef = signal('');

  /** Straight from `ProposalDetail.disclosures_complete` -- the same flag
   * `IssuanceService.launch` itself gates on server-side, never re-derived here. */
  readonly isLaunchable = computed(() => this.proposal()?.disclosures_complete ?? false);

  private get proposalId(): number {
    return Number(this.route.snapshot.paramMap.get('id'));
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    this.issuanceService
      .fetchProposal(this.proposalId)
      .then(() => this.state.set('loaded'))
      .catch(() => this.state.set('error'));
  }

  onDisclosureUploaded(): void {
    this.load();
  }

  async approve(): Promise<void> {
    await this.run(() => this.issuanceService.complianceApprove(this.proposalId));
  }

  async reject(): Promise<void> {
    const reason = this.rejectReason().trim();
    if (!reason) {
      return;
    }
    await this.run(() => this.issuanceService.reject(this.proposalId, reason));
  }

  async recordFiling(): Promise<void> {
    const reference = this.filingReference().trim();
    if (!reference) {
      return;
    }
    await this.run(() => this.issuanceService.fileIfsca(this.proposalId, reference));
  }

  async recordApproval(): Promise<void> {
    const reference = this.approvalReference().trim();
    if (!reference) {
      return;
    }
    await this.run(() => this.issuanceService.ifscaApprove(this.proposalId, reference));
  }

  async launch(): Promise<void> {
    const symbol = this.launchSymbol().trim();
    if (!symbol || !this.isLaunchable()) {
      return;
    }
    const contractAddress = this.launchContractAddress().trim();
    await this.run(() =>
      this.issuanceService.launch(this.proposalId, contractAddress ? { symbol, contract_address: contractAddress } : { symbol }),
    );
  }

  async toggleCircuitBreaker(): Promise<void> {
    const series = this.tokenSeries();
    if (!series || this.togglingCircuitBreaker()) {
      return;
    }
    this.togglingCircuitBreaker.set(true);
    try {
      if (series.paused) {
        await this.issuanceService.resumeTokenSeries(series.id);
      } else {
        await this.issuanceService.pauseTokenSeries(series.id);
      }
    } finally {
      this.togglingCircuitBreaker.set(false);
    }
  }

  async loadTokenSeriesById(): Promise<void> {
    const id = Number(this.tokenSeriesIdLookup());
    if (!id || this.loadingTokenSeries()) {
      return;
    }
    this.loadingTokenSeries.set(true);
    try {
      await this.issuanceService.getTokenSeries(id);
    } finally {
      this.loadingTokenSeries.set(false);
    }
  }

  async recordDeployment(): Promise<void> {
    const series = this.tokenSeries();
    const bytecodeHash = this.deploymentBytecodeHash().trim();
    const version = this.deploymentVersion().trim();
    if (!series || !bytecodeHash || !version || this.recordingDeployment()) {
      return;
    }
    const auditRef = this.deploymentAuditRef().trim();
    this.recordingDeployment.set(true);
    try {
      await this.issuanceService.recordSmartContractDeployment(
        series.id,
        auditRef ? { bytecode_hash: bytecodeHash, version, audit_report_ref: auditRef } : { bytecode_hash: bytecodeHash, version },
      );
      this.deploymentBytecodeHash.set('');
      this.deploymentVersion.set('');
      this.deploymentAuditRef.set('');
    } finally {
      this.recordingDeployment.set(false);
    }
  }

  private async run(action: () => Promise<unknown>): Promise<void> {
    this.actioning.set(true);
    try {
      await action();
    } finally {
      this.actioning.set(false);
    }
  }
}
