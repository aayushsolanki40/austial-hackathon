import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { environment } from '../../../../environments/environment';
import { ProposalListResponse, TokenizationProposal } from '../../../core/issuance/issuance.models';
import IssuancePipelineComponent from './issuance-pipeline.component';

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

function proposalListResponse(items: TokenizationProposal[]): ProposalListResponse {
  return { total: items.length, items };
}

describe('IssuancePipelineComponent', () => {
  let fixture: ComponentFixture<IssuancePipelineComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IssuancePipelineComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(IssuancePipelineComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function expectPipelineReq() {
    return httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/issuance/proposals`);
  }

  it('groups proposals into every status column, including empty ones', fakeAsync(() => {
    fixture.detectChanges();
    expectPipelineReq().flush(
      proposalListResponse([proposal({ id: 1, status: 'DRAFT' }), proposal({ id: 2, status: 'DOCUMENTATION_REVIEW' })]),
    );
    flushMicrotasks();

    const component = fixture.componentInstance;
    expect(component.state()).toBe('loaded');
    expect(component.pipelineByStatus()['DRAFT'].length).toBe(1);
    expect(component.pipelineByStatus()['DOCUMENTATION_REVIEW'].length).toBe(1);
    expect(component.pipelineByStatus()['LAUNCHED'].length).toBe(0);
    expect(component.pipelineByStatus()['REJECTED'].length).toBe(0);
  }));

  it('falls back to the error state when the proposals endpoint is unavailable', fakeAsync(() => {
    fixture.detectChanges();
    expectPipelineReq().flush('forbidden', { status: 403, statusText: 'Forbidden' });
    flushMicrotasks();

    expect(fixture.componentInstance.state()).toBe('error');
  }));

  it('approve() POSTs /issuance/proposals/:id/compliance-approve', fakeAsync(() => {
    fixture.detectChanges();
    expectPipelineReq().flush(proposalListResponse([proposal({ status: 'DOCUMENTATION_REVIEW' })]));

    const component = fixture.componentInstance;
    component.approve(proposal({ status: 'DOCUMENTATION_REVIEW' }));
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/compliance-approve`);
    expect(req.request.method).toBe('POST');
    req.flush(proposal({ status: 'COMPLIANCE_APPROVED' }));
    flushMicrotasks();

    expect(component.actioningId()).toBeNull();
  }));

  it('reject() is a no-op without a reason, and POSTs with one once set', fakeAsync(() => {
    fixture.detectChanges();
    expectPipelineReq().flush(proposalListResponse([proposal({ status: 'DOCUMENTATION_REVIEW' })]));

    const component = fixture.componentInstance;
    component.reject(proposal({ status: 'DOCUMENTATION_REVIEW' }));
    httpMock.expectNone(`${environment.apiBaseUrl}/issuance/proposals/1/reject`);

    component.setReason(1, 'Prospectus incomplete.');
    component.reject(proposal({ status: 'DOCUMENTATION_REVIEW' }));
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/reject`);
    expect(req.request.body).toEqual({ reason: 'Prospectus incomplete.' });
    req.flush(proposal({ status: 'REJECTED', rejection_reason: 'Prospectus incomplete.' }));
    flushMicrotasks();
  }));

  it('recordFiling() POSTs /issuance/proposals/:id/file-ifsca with filing_reference', fakeAsync(() => {
    fixture.detectChanges();
    expectPipelineReq().flush(proposalListResponse([proposal({ status: 'COMPLIANCE_APPROVED' })]));

    const component = fixture.componentInstance;
    component.setFilingReference(1, 'IFSCA/FILING/0042');
    component.recordFiling(proposal({ status: 'COMPLIANCE_APPROVED' }));
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/file-ifsca`);
    expect(req.request.body).toEqual({ filing_reference: 'IFSCA/FILING/0042' });
    req.flush(proposal({ status: 'IFSCA_FILED', ifsca_filing_reference: 'IFSCA/FILING/0042' }));
    flushMicrotasks();
  }));

  it('recordApproval() POSTs /issuance/proposals/:id/ifsca-approve with approval_reference', fakeAsync(() => {
    fixture.detectChanges();
    expectPipelineReq().flush(proposalListResponse([proposal({ status: 'IFSCA_FILED' })]));

    const component = fixture.componentInstance;
    component.setApprovalReference(1, 'IFSCA/APPROVAL/0042');
    component.recordApproval(proposal({ status: 'IFSCA_FILED' }));
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/ifsca-approve`);
    expect(req.request.body).toEqual({ approval_reference: 'IFSCA/APPROVAL/0042' });
    req.flush(proposal({ status: 'IFSCA_APPROVED', ifsca_approval_reference: 'IFSCA/APPROVAL/0042' }));
    flushMicrotasks();
  }));
});
