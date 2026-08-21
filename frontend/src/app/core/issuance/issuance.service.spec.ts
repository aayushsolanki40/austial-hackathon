import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { DisclosureDocument, ProposalDetail, ProposalListResponse, TokenSeries, TokenizationProposal } from './issuance.models';
import { IssuanceService } from './issuance.service';

function proposal(overrides: Partial<TokenizationProposal> = {}): TokenizationProposal {
  return {
    id: 1,
    asset_id: 1,
    issuer_id: 1,
    status: 'DRAFT',
    total_units: 10000,
    unit_price_usd: 100,
    min_subscription_units: 10,
    subscription_start_at: '2026-09-01T00:00:00Z',
    subscription_end_at: '2026-09-30T00:00:00Z',
    ifsca_filing_reference: null,
    ifsca_approval_reference: null,
    rejection_reason: null,
    reviewed_by_user_id: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function proposalDetail(overrides: Partial<ProposalDetail> = {}): ProposalDetail {
  return {
    ...proposal(),
    disclosures: [],
    missing_disclosure_types: ['RISK', 'FEE', 'LIQUIDITY', 'CUSTODY', 'TAX', 'PROSPECTUS'],
    disclosures_complete: false,
    ...overrides,
  };
}

function proposalListResponse(items: TokenizationProposal[]): ProposalListResponse {
  return { total: items.length, items };
}

function disclosureDocument(overrides: Partial<DisclosureDocument> = {}): DisclosureDocument {
  return {
    id: 1,
    disclosure_type: 'RISK',
    object_key: 'disclosures/1/risk.pdf',
    version: 1,
    is_current: true,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function tokenSeries(overrides: Partial<TokenSeries> = {}): TokenSeries {
  return {
    id: 1,
    proposal_id: 1,
    symbol: 'MCT',
    total_supply: 10000,
    contract_address: null,
    paused: false,
    smart_contract_deployment_id: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('IssuanceService', () => {
  let service: IssuanceService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(IssuanceService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('starts with empty proposal lists and no current proposal/token series', () => {
    expect(service.myProposals()).toEqual([]);
    expect(service.pipeline()).toEqual([]);
    expect(service.current()).toBeNull();
    expect(service.currentTokenSeries()).toBeNull();
  });

  // -- issuer-facing (proposals/mine) ---------------------------------------------------------

  it('listMyProposals() GETs /issuance/proposals/mine and stores the unwrapped items', async () => {
    const promise = service.listMyProposals();
    const req = httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/issuance/proposals/mine`);
    expect(req.request.method).toBe('GET');
    req.flush(proposalListResponse([proposal()]));

    const result = await promise;
    expect(result.length).toBe(1);
    expect(service.myProposals()[0].id).toBe(1);
  });

  it('createProposal() POSTs /issuance/proposals and prepends the response', async () => {
    const promise = service.createProposal({
      asset_id: 1,
      total_units: 10000,
      unit_price_usd: 100,
      min_subscription_units: 10,
      subscription_start_at: '2026-09-01',
      subscription_end_at: '2026-09-30',
    });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals`);
    expect(req.request.method).toBe('POST');
    req.flush(proposalDetail());

    const result = await promise;
    expect(result.id).toBe(1);
    expect(service.myProposals()[0].status).toBe('DRAFT');
  });

  it('fetchMyProposal() GETs /issuance/proposals/mine/:id and sets current', async () => {
    const promise = service.fetchMyProposal(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1`);
    expect(req.request.method).toBe('GET');
    req.flush(proposalDetail());

    const result = await promise;
    expect(result.id).toBe(1);
    expect(service.current()?.id).toBe(1);
  });

  it('submitForReview() POSTs /issuance/proposals/mine/:id/submit', async () => {
    const promise = service.submitForReview(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1/submit`);
    expect(req.request.method).toBe('POST');
    req.flush(proposalDetail({ status: 'DOCUMENTATION_REVIEW' }));

    const result = await promise;
    expect(result.status).toBe('DOCUMENTATION_REVIEW');
  });

  it('requestDisclosureUpload() POSTs /issuance/proposals/mine/:id/disclosures/upload-url', async () => {
    const promise = service.requestDisclosureUpload(1, { disclosure_type: 'RISK', content_type: 'application/pdf' });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1/disclosures/upload-url`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ disclosure_type: 'RISK', content_type: 'application/pdf' });
    req.flush({ upload_url: 'https://s3.example/presigned', object_key: 'disclosures/1/risk.pdf' });

    const result = await promise;
    expect(result.object_key).toBe('disclosures/1/risk.pdf');
  });

  it('addDisclosure() POSTs /issuance/proposals/mine/:id/disclosures without patching current', async () => {
    const fetchPromise = service.fetchMyProposal(1);
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1`).flush(proposalDetail());
    await fetchPromise;

    const promise = service.addDisclosure(1, { disclosure_type: 'RISK', object_key: 'disclosures/1/risk.pdf' });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1/disclosures`);
    expect(req.request.method).toBe('POST');
    req.flush(disclosureDocument());

    const result = await promise;
    expect(result.disclosure_type).toBe('RISK');
    // addDisclosure() does not patch `current` -- callers refetch the proposal detail
    // afterwards to get the server-recomputed missing_disclosure_types/disclosures_complete.
    expect(service.current()?.disclosures.length).toBe(0);
  });

  // -- compliance/admin-facing (proposals, no /mine) ------------------------------------------

  it('listPipeline() GETs /issuance/proposals (no /review-queue) and groups by status', async () => {
    const promise = service.listPipeline();
    const req = httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/issuance/proposals`);
    expect(req.request.method).toBe('GET');
    req.flush(proposalListResponse([proposal({ id: 1, status: 'DRAFT' }), proposal({ id: 2, status: 'IFSCA_APPROVED' })]));

    await promise;
    expect(service.pipeline().length).toBe(2);
    expect(service.pipelineByStatus()['DRAFT'].length).toBe(1);
    expect(service.pipelineByStatus()['IFSCA_APPROVED'].length).toBe(1);
    expect(service.pipelineByStatus()['LAUNCHED'].length).toBe(0);
  });

  it('listPipeline(status) passes an optional status query filter', async () => {
    const promise = service.listPipeline('DRAFT');
    const req = httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/issuance/proposals` && r.params.get('status') === 'DRAFT');
    req.flush(proposalListResponse([proposal({ status: 'DRAFT' })]));
    await promise;

    expect(service.pipeline().length).toBe(1);
    expect(service.pipeline()[0].status).toBe('DRAFT');
  });

  it('fetchProposal() GETs /issuance/proposals/:id and sets current', async () => {
    const promise = service.fetchProposal(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1`);
    expect(req.request.method).toBe('GET');
    req.flush(proposalDetail());

    const result = await promise;
    expect(result.id).toBe(1);
    expect(service.current()?.id).toBe(1);
  });

  it('complianceApprove() POSTs /issuance/proposals/:id/compliance-approve and updates current + pipeline in place', async () => {
    const listPromise = service.listPipeline();
    httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/issuance/proposals`).flush(
      proposalListResponse([proposal({ status: 'DOCUMENTATION_REVIEW' })]),
    );
    await listPromise;

    const promise = service.complianceApprove(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/compliance-approve`);
    expect(req.request.method).toBe('POST');
    req.flush(proposalDetail({ status: 'COMPLIANCE_APPROVED' }));

    await promise;
    expect(service.pipeline()[0].status).toBe('COMPLIANCE_APPROVED');
  });

  it('reject() POSTs /issuance/proposals/:id/reject with the reason', async () => {
    const promise = service.reject(1, 'Prospectus incomplete.');
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/reject`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ reason: 'Prospectus incomplete.' });
    req.flush(proposalDetail({ status: 'REJECTED', rejection_reason: 'Prospectus incomplete.' }));

    const result = await promise;
    expect(result.status).toBe('REJECTED');
  });

  it('fileIfsca() POSTs /issuance/proposals/:id/file-ifsca with filing_reference', async () => {
    const promise = service.fileIfsca(1, 'IFSCA/FILING/0042');
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/file-ifsca`);
    expect(req.request.body).toEqual({ filing_reference: 'IFSCA/FILING/0042' });
    req.flush(proposalDetail({ status: 'IFSCA_FILED', ifsca_filing_reference: 'IFSCA/FILING/0042' }));

    const result = await promise;
    expect(result.status).toBe('IFSCA_FILED');
  });

  it('ifscaApprove() POSTs /issuance/proposals/:id/ifsca-approve with approval_reference', async () => {
    const promise = service.ifscaApprove(1, 'IFSCA/APPROVAL/0042');
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/ifsca-approve`);
    expect(req.request.body).toEqual({ approval_reference: 'IFSCA/APPROVAL/0042' });
    req.flush(proposalDetail({ status: 'IFSCA_APPROVED', ifsca_approval_reference: 'IFSCA/APPROVAL/0042' }));

    const result = await promise;
    expect(result.status).toBe('IFSCA_APPROVED');
  });

  it('launch() POSTs /issuance/proposals/:id/launch with symbol/contract_address, returns TokenSeries, and patches the proposal status locally', async () => {
    const fetchPromise = service.fetchProposal(1);
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1`).flush(proposalDetail({ status: 'IFSCA_APPROVED', disclosures_complete: true }));
    await fetchPromise;

    const promise = service.launch(1, { symbol: 'MCT', contract_address: '0xabc' });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/launch`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ symbol: 'MCT', contract_address: '0xabc' });
    req.flush(tokenSeries());

    const result = await promise;
    expect(result.symbol).toBe('MCT');
    expect(service.currentTokenSeries()?.symbol).toBe('MCT');
    expect(service.current()?.status).toBe('LAUNCHED');
  });

  // -- token series ------------------------------------------------------------------------------

  it('getTokenSeries() GETs /issuance/token-series/:id', async () => {
    const promise = service.getTokenSeries(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/token-series/1`);
    expect(req.request.method).toBe('GET');
    req.flush(tokenSeries());

    await promise;
    expect(service.currentTokenSeries()?.id).toBe(1);
  });

  it('pauseTokenSeries() POSTs /issuance/token-series/:id/pause', async () => {
    const promise = service.pauseTokenSeries(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/token-series/1/pause`);
    expect(req.request.method).toBe('POST');
    req.flush(tokenSeries({ paused: true }));

    await promise;
    expect(service.currentTokenSeries()?.paused).toBeTrue();
  });

  it('resumeTokenSeries() POSTs /issuance/token-series/:id/resume (not /unpause)', async () => {
    const promise = service.resumeTokenSeries(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/token-series/1/resume`);
    expect(req.request.method).toBe('POST');
    req.flush(tokenSeries({ paused: false }));

    await promise;
    expect(service.currentTokenSeries()?.paused).toBeFalse();
  });

  it('recordSmartContractDeployment() POSTs /issuance/token-series/:id/smart-contract-deployment', async () => {
    const promise = service.recordSmartContractDeployment(1, { bytecode_hash: '0xhash', version: 'v1' });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/token-series/1/smart-contract-deployment`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ bytecode_hash: '0xhash', version: 'v1' });
    req.flush(tokenSeries({ smart_contract_deployment_id: 9 }));

    const result = await promise;
    expect(result.smart_contract_deployment_id).toBe(9);
    expect(service.currentTokenSeries()?.smart_contract_deployment_id).toBe(9);
  });
});
