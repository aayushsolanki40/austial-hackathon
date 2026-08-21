import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiService } from '../api/api.service';
import {
  AddDisclosureRequest,
  CreateProposalRequest,
  DisclosureDocument,
  DisclosureUploadUrlRequest,
  DisclosureUploadUrlResponse,
  ProposalDetail,
  ProposalListResponse,
  ProposalStatus,
  RecordSmartContractDeploymentRequest,
  TokenSeries,
  TokenizationProposal,
} from './issuance.models';

const PROPOSAL_PAGE_SIZE = 100;

/** Kanban column order per the build plan's Phase 4 state machine, `REJECTED` last as its own
 * terminal bucket rather than slotted between the stages it can branch from. */
export const PIPELINE_STATUS_COLUMNS: ProposalStatus[] = [
  'DRAFT',
  'DOCUMENTATION_REVIEW',
  'COMPLIANCE_APPROVED',
  'IFSCA_FILED',
  'IFSCA_APPROVED',
  'LAUNCHED',
  'REJECTED',
];

/**
 * Signal-based `TokenizationProposal` state + calls to the real backend `issuance` module
 * (`backend/src/modules/issuance/`, contract confirmed against
 * `issuance_controller.py`/`issuance_dto.py`). Mirrors `KycService`/`IssuerService`'s
 * established shape: signals for local state, `ApiService` for HTTP, consumed by both the
 * issuer-facing proposal screens and the compliance-facing kanban/review screens.
 *
 * Route split reflects the real controller's two role-gated route families:
 *   - `proposals/mine...` -- issuer-facing self-service (`@Roles("ISSUER")`): list/get/submit/
 *     disclosures scoped to the caller's own proposals.
 *   - `proposals...` (no `/mine`) -- compliance-officer/admin-facing
 *     (`@Roles("COMPLIANCE_OFFICER", "ADMIN")`): list-all/get-any/approve/reject/file/launch.
 *
 * State signals:
 *   - `myProposals` -- the issuer's own proposals (`GET /issuance/proposals/mine`).
 *   - `pipeline` -- every proposal across every issuer, for the compliance kanban
 *     (`GET /issuance/proposals`, optional `status` filter omitted here so the kanban can group
 *     every column client-side from a single fetch).
 *   - `current` -- whichever single proposal's *detail* (`ProposalDetail`, with the
 *     server-computed disclosure checklist) a detail screen has open, shared by both the
 *     issuer's own detail view and the admin review screen.
 *   - `currentTokenSeries` -- the `TokenSeries` for whichever proposal is open, if it has been
 *     launched. `TokenSeries` is a standalone resource (its own `GET /token-series/:id`) with
 *     no back-reference on `ProposalDetail`, so this is populated either by `launch()`'s
 *     response or by an explicit `getTokenSeries(id)` lookup -- there is no way to resolve a
 *     proposal's token-series id from the proposal alone per the real contract.
 */
@Injectable({ providedIn: 'root' })
export class IssuanceService {
  private readonly api = inject(ApiService);
  private readonly http = inject(HttpClient);

  private readonly myProposalsSignal = signal<TokenizationProposal[]>([]);
  private readonly pipelineSignal = signal<TokenizationProposal[]>([]);
  private readonly currentSignal = signal<ProposalDetail | null>(null);
  private readonly currentTokenSeriesSignal = signal<TokenSeries | null>(null);
  private readonly loadingSignal = signal(false);

  readonly myProposals = this.myProposalsSignal.asReadonly();
  readonly pipeline = this.pipelineSignal.asReadonly();
  readonly current = this.currentSignal.asReadonly();
  readonly currentTokenSeries = this.currentTokenSeriesSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();

  /** `pipeline()` grouped by status for the kanban board -- every column present (even
   * empty) so the template can render a fixed set of columns without guarding on presence. */
  readonly pipelineByStatus = computed<Record<ProposalStatus, TokenizationProposal[]>>(() => {
    const groups = Object.fromEntries(PIPELINE_STATUS_COLUMNS.map((status) => [status, [] as TokenizationProposal[]])) as Record<
      ProposalStatus,
      TokenizationProposal[]
    >;
    for (const proposal of this.pipelineSignal()) {
      (groups[proposal.status] ?? (groups[proposal.status] = [])).push(proposal);
    }
    return groups;
  });

  // -- issuer-facing (proposals/mine) --------------------------------------------------------

  /** `GET /issuance/proposals/mine` -- the caller's own proposals. Unwraps
   * `ProposalListDto.items`. */
  async listMyProposals(): Promise<TokenizationProposal[]> {
    this.loadingSignal.set(true);
    try {
      const response = await firstValueFrom(
        this.api.get<ProposalListResponse>('/issuance/proposals/mine', { skip: 0, take: PROPOSAL_PAGE_SIZE }),
      );
      this.myProposalsSignal.set(response.items);
      return response.items;
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /** `POST /issuance/proposals`. Same path for every caller (the backend scopes the created
   * proposal to the authenticated issuer server-side) -- returns the full `ProposalDetail`. */
  async createProposal(request: CreateProposalRequest): Promise<ProposalDetail> {
    const proposal = await firstValueFrom(this.api.post<ProposalDetail>('/issuance/proposals', request));
    this.myProposalsSignal.update((proposals) => [proposal, ...proposals]);
    return proposal;
  }

  /** `GET /issuance/proposals/mine/:id`. Sets `current`. */
  async fetchMyProposal(id: number): Promise<ProposalDetail> {
    const proposal = await firstValueFrom(this.api.get<ProposalDetail>(`/issuance/proposals/mine/${id}`));
    this.currentSignal.set(proposal);
    return proposal;
  }

  /** `POST /issuance/proposals/mine/:id/submit` -- `DRAFT -> DOCUMENTATION_REVIEW`. */
  async submitForReview(id: number): Promise<ProposalDetail> {
    return this.mutateMine(id, 'submit');
  }

  /** Step 1 of the direct-to-S3 disclosure upload flow, mirroring `KycService`'s
   * `requestDocumentUpload`. Issuer-only (`proposals/mine/...`). */
  async requestDisclosureUpload(proposalId: number, request: DisclosureUploadUrlRequest): Promise<DisclosureUploadUrlResponse> {
    return firstValueFrom(
      this.api.post<DisclosureUploadUrlResponse>(`/issuance/proposals/mine/${proposalId}/disclosures/upload-url`, request),
    );
  }

  /** Step 2: PUT the file straight to S3, never routed through `ApiService`/the backend
   * origin -- same reasoning as `KycService.uploadToPresignedUrl`. */
  async uploadToPresignedUrl(uploadUrl: string, body: Blob, contentType: string): Promise<void> {
    await firstValueFrom(this.http.put(uploadUrl, body, { headers: { 'Content-Type': contentType } }));
  }

  /** Step 3: confirm the direct upload finished (`AddDisclosureDto`). The response is just the
   * new `DisclosureDocument`, not an updated completeness checklist -- callers should refetch
   * the owning proposal (`fetchMyProposal`/`fetchProposal`) afterwards to get the fresh
   * server-computed `missing_disclosure_types`/`disclosures_complete` rather than patching them
   * client-side. */
  async addDisclosure(proposalId: number, request: AddDisclosureRequest): Promise<DisclosureDocument> {
    return firstValueFrom(this.api.post<DisclosureDocument>(`/issuance/proposals/mine/${proposalId}/disclosures`, request));
  }

  // -- compliance/admin-facing (proposals, no /mine) -----------------------------------------

  /** `GET /issuance/proposals?status=&skip=&take=` -- every proposal across every issuer.
   * `status` is an optional server-side filter; omitted here so a single fetch can populate
   * every kanban column client-side via `pipelineByStatus`. Unwraps `ProposalListDto.items`. */
  async listPipeline(status?: ProposalStatus): Promise<TokenizationProposal[]> {
    this.loadingSignal.set(true);
    try {
      const response = await firstValueFrom(
        this.api.get<ProposalListResponse>('/issuance/proposals', { status, skip: 0, take: PROPOSAL_PAGE_SIZE }),
      );
      this.pipelineSignal.set(response.items);
      return response.items;
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /** `GET /issuance/proposals/:id`. Sets `current`. */
  async fetchProposal(id: number): Promise<ProposalDetail> {
    const proposal = await firstValueFrom(this.api.get<ProposalDetail>(`/issuance/proposals/${id}`));
    this.currentSignal.set(proposal);
    return proposal;
  }

  /** `POST /issuance/proposals/:id/compliance-approve` -- `DOCUMENTATION_REVIEW ->
   * COMPLIANCE_APPROVED`. */
  async complianceApprove(id: number): Promise<ProposalDetail> {
    return this.mutate(id, 'compliance-approve');
  }

  /** `POST /issuance/proposals/:id/reject` -- `DOCUMENTATION_REVIEW | IFSCA_FILED ->
   * REJECTED`. */
  async reject(id: number, reason: string): Promise<ProposalDetail> {
    return this.mutate(id, 'reject', { reason });
  }

  /** `POST /issuance/proposals/:id/file-ifsca` -- `COMPLIANCE_APPROVED -> IFSCA_FILED`. */
  async fileIfsca(id: number, filingReference: string): Promise<ProposalDetail> {
    return this.mutate(id, 'file-ifsca', { filing_reference: filingReference });
  }

  /** `POST /issuance/proposals/:id/ifsca-approve` -- `IFSCA_FILED -> IFSCA_APPROVED`. */
  async ifscaApprove(id: number, approvalReference: string): Promise<ProposalDetail> {
    return this.mutate(id, 'ifsca-approve', { approval_reference: approvalReference });
  }

  /** `POST /issuance/proposals/:id/launch` -- `IFSCA_APPROVED -> LAUNCHED`, atomically
   * creating the `TokenSeries`. Gated server-side on `disclosures_complete` (422 otherwise);
   * the caller should also check `proposal.disclosures_complete` client-side to disable the
   * action ahead of that round trip. Unlike every other proposal action, this endpoint's
   * response is the `TokenSeries` itself, not a `ProposalDetail` -- the proposal's `status` is
   * patched to `LAUNCHED` locally rather than round-tripped, since the server doesn't hand back
   * an updated proposal here. */
  async launch(id: number, request: { symbol: string; contract_address?: string }): Promise<TokenSeries> {
    const series = await firstValueFrom(this.api.post<TokenSeries>(`/issuance/proposals/${id}/launch`, request));
    this.currentTokenSeriesSignal.set(series);
    this.patchProposalStatus(id, 'LAUNCHED');
    return series;
  }

  // -- token series: circuit breaker + smart contract deployment ------------------------------

  /** `GET /issuance/token-series/:id`. There is no listing/lookup-by-proposal endpoint, so
   * this is only reachable when the caller already knows the token-series id (e.g. from a
   * `launch()` response held this session, or entered manually when revisiting an already-
   * launched proposal in a fresh session). */
  async getTokenSeries(id: number): Promise<TokenSeries> {
    const series = await firstValueFrom(this.api.get<TokenSeries>(`/issuance/token-series/${id}`));
    this.currentTokenSeriesSignal.set(series);
    return series;
  }

  /** `POST /issuance/token-series/:id/pause` -- the build plan's circuit-breaker control,
   * letting a Compliance Officer pause a launched `TokenSeries` without redeploy. */
  async pauseTokenSeries(id: number): Promise<TokenSeries> {
    return this.setTokenSeries(id, 'pause');
  }

  /** `POST /issuance/token-series/:id/resume`. */
  async resumeTokenSeries(id: number): Promise<TokenSeries> {
    return this.setTokenSeries(id, 'resume');
  }

  /** `POST /issuance/token-series/:id/smart-contract-deployment` -- optional record of the
   * on-chain deployment backing this `TokenSeries` (not required to launch). */
  async recordSmartContractDeployment(id: number, request: RecordSmartContractDeploymentRequest): Promise<TokenSeries> {
    const series = await firstValueFrom(this.api.post<TokenSeries>(`/issuance/token-series/${id}/smart-contract-deployment`, request));
    this.currentTokenSeriesSignal.set(series);
    return series;
  }

  private async setTokenSeries(id: number, action: 'pause' | 'resume'): Promise<TokenSeries> {
    const series = await firstValueFrom(this.api.post<TokenSeries>(`/issuance/token-series/${id}/${action}`));
    this.currentTokenSeriesSignal.set(series);
    return series;
  }

  // -- shared helpers --------------------------------------------------------------------------

  /** `:id/<action>` mutation under the issuer-facing `proposals/mine/...` route family. */
  private async mutateMine(id: number, action: string, body: Record<string, unknown> = {}): Promise<ProposalDetail> {
    const proposal = await firstValueFrom(this.api.post<ProposalDetail>(`/issuance/proposals/mine/${id}/${action}`, body));
    this.replaceEverywhere(proposal);
    return proposal;
  }

  /** `:id/<action>` mutation under the compliance/admin-facing `proposals/...` route family.
   * Updates `current` plus both list signals in place with the response so kanban/list views
   * don't need a full refetch after every action. */
  private async mutate(id: number, action: string, body: Record<string, unknown> = {}): Promise<ProposalDetail> {
    const proposal = await firstValueFrom(this.api.post<ProposalDetail>(`/issuance/proposals/${id}/${action}`, body));
    this.replaceEverywhere(proposal);
    return proposal;
  }

  private replaceEverywhere(proposal: ProposalDetail): void {
    if (this.currentSignal()?.id === proposal.id) {
      this.currentSignal.set(proposal);
    }
    this.myProposalsSignal.update((proposals) => proposals.map((p) => (p.id === proposal.id ? proposal : p)));
    this.pipelineSignal.update((proposals) => proposals.map((p) => (p.id === proposal.id ? proposal : p)));
  }

  private patchProposalStatus(id: number, status: ProposalStatus): void {
    const current = this.currentSignal();
    if (current?.id === id) {
      this.currentSignal.set({ ...current, status });
    }
    this.myProposalsSignal.update((proposals) => proposals.map((p) => (p.id === id ? { ...p, status } : p)));
    this.pipelineSignal.update((proposals) => proposals.map((p) => (p.id === id ? { ...p, status } : p)));
  }
}
