import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { environment } from '../../../../environments/environment';
import { ProposalDetail, TokenSeries } from '../../../core/issuance/issuance.models';
import ProposalReviewComponent from './proposal-review.component';

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

function proposal(overrides: Partial<ProposalDetail> = {}): ProposalDetail {
  return {
    id: 1,
    asset_id: 1,
    issuer_id: 1,
    status: 'DOCUMENTATION_REVIEW',
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
    disclosures: [],
    missing_disclosure_types: ['RISK', 'FEE', 'LIQUIDITY', 'CUSTODY', 'TAX', 'PROSPECTUS'],
    disclosures_complete: false,
    ...overrides,
  };
}

describe('ProposalReviewComponent', () => {
  let fixture: ComponentFixture<ProposalReviewComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProposalReviewComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: '1' }) } },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ProposalReviewComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('loads the proposal by id from /issuance/proposals/:id', fakeAsync(() => {
    fixture.detectChanges();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1`);
    req.flush(proposal());
    flushMicrotasks();

    expect(fixture.componentInstance.state()).toBe('loaded');
    expect(fixture.componentInstance.proposal()?.id).toBe(1);
  }));

  it('approve() POSTs /issuance/proposals/:id/compliance-approve', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1`).flush(proposal({ status: 'DOCUMENTATION_REVIEW' }));
    flushMicrotasks();

    fixture.componentInstance.approve();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/compliance-approve`);
    expect(req.request.method).toBe('POST');
    req.flush(proposal({ status: 'COMPLIANCE_APPROVED' }));
    flushMicrotasks();

    expect(fixture.componentInstance.proposal()?.status).toBe('COMPLIANCE_APPROVED');
  }));

  it('reject() is a no-op without a reason', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1`).flush(proposal({ status: 'DOCUMENTATION_REVIEW' }));
    flushMicrotasks();

    fixture.componentInstance.reject();
    expect(fixture.componentInstance.actioning()).toBeFalse();
    httpMock.expectNone(`${environment.apiBaseUrl}/issuance/proposals/1/reject`);
  }));

  it('recordFiling() POSTs /issuance/proposals/:id/file-ifsca', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1`).flush(proposal({ status: 'COMPLIANCE_APPROVED' }));
    flushMicrotasks();

    fixture.componentInstance.filingReference.set('IFSCA/FILING/0042');
    fixture.componentInstance.recordFiling();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/file-ifsca`);
    expect(req.request.body).toEqual({ filing_reference: 'IFSCA/FILING/0042' });
    req.flush(proposal({ status: 'IFSCA_FILED', ifsca_filing_reference: 'IFSCA/FILING/0042' }));
    flushMicrotasks();
  }));

  it('recordApproval() POSTs /issuance/proposals/:id/ifsca-approve', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1`).flush(proposal({ status: 'IFSCA_FILED' }));
    flushMicrotasks();

    fixture.componentInstance.approvalReference.set('IFSCA/APPROVAL/0042');
    fixture.componentInstance.recordApproval();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/ifsca-approve`);
    expect(req.request.body).toEqual({ approval_reference: 'IFSCA/APPROVAL/0042' });
    req.flush(proposal({ status: 'IFSCA_APPROVED', ifsca_approval_reference: 'IFSCA/APPROVAL/0042' }));
    flushMicrotasks();
  }));

  it('launch() is disabled until disclosures_complete is true and a symbol is entered', fakeAsync(() => {
    fixture.detectChanges();
    httpMock
      .expectOne(`${environment.apiBaseUrl}/issuance/proposals/1`)
      .flush(proposal({ status: 'IFSCA_APPROVED', disclosures: [], missing_disclosure_types: ['RISK'], disclosures_complete: false }));
    flushMicrotasks();

    expect(fixture.componentInstance.isLaunchable()).toBeFalse();
    fixture.componentInstance.launchSymbol.set('MCT');
    fixture.componentInstance.launch();
    httpMock.expectNone(`${environment.apiBaseUrl}/issuance/proposals/1/launch`);
  }));

  it('launch() POSTs /issuance/proposals/:id/launch with symbol + contract_address and stores the returned TokenSeries', fakeAsync(() => {
    fixture.detectChanges();
    httpMock
      .expectOne(`${environment.apiBaseUrl}/issuance/proposals/1`)
      .flush(proposal({ status: 'IFSCA_APPROVED', disclosures: [], missing_disclosure_types: [], disclosures_complete: true }));
    flushMicrotasks();

    const component = fixture.componentInstance;
    expect(component.isLaunchable()).toBeTrue();
    component.launchSymbol.set('MCT');
    component.launchContractAddress.set('0xabc');
    component.launch();

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/launch`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ symbol: 'MCT', contract_address: '0xabc' });
    req.flush(tokenSeries());
    flushMicrotasks();

    expect(component.tokenSeries()?.symbol).toBe('MCT');
    expect(component.proposal()?.status).toBe('LAUNCHED');
  }));

  it('toggleCircuitBreaker() pauses an active LAUNCHED token series', fakeAsync(() => {
    fixture.detectChanges();
    httpMock
      .expectOne(`${environment.apiBaseUrl}/issuance/proposals/1`)
      .flush(proposal({ status: 'IFSCA_APPROVED', missing_disclosure_types: [], disclosures_complete: true }));
    flushMicrotasks();

    const component = fixture.componentInstance;
    component.launchSymbol.set('MCT');
    component.launch();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/launch`).flush(tokenSeries({ paused: false }));
    flushMicrotasks();

    component.toggleCircuitBreaker();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/token-series/1/pause`);
    expect(req.request.method).toBe('POST');
    req.flush(tokenSeries({ paused: true }));
    flushMicrotasks();

    expect(component.tokenSeries()?.paused).toBeTrue();
  }));

  it('toggleCircuitBreaker() resumes a paused LAUNCHED token series', fakeAsync(() => {
    fixture.detectChanges();
    httpMock
      .expectOne(`${environment.apiBaseUrl}/issuance/proposals/1`)
      .flush(proposal({ status: 'IFSCA_APPROVED', missing_disclosure_types: [], disclosures_complete: true }));
    flushMicrotasks();

    const component = fixture.componentInstance;
    component.launchSymbol.set('MCT');
    component.launch();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1/launch`).flush(tokenSeries({ paused: true }));
    flushMicrotasks();

    component.toggleCircuitBreaker();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/token-series/1/resume`);
    expect(req.request.method).toBe('POST');
    req.flush(tokenSeries({ paused: false }));
    flushMicrotasks();

    expect(component.tokenSeries()?.paused).toBeFalse();
  }));

  it('loadTokenSeriesById() GETs /issuance/token-series/:id', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1`).flush(proposal({ status: 'LAUNCHED' }));
    flushMicrotasks();

    const component = fixture.componentInstance;
    component.tokenSeriesIdLookup.set('7');
    component.loadTokenSeriesById();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/token-series/7`);
    expect(req.request.method).toBe('GET');
    req.flush(tokenSeries({ id: 7 }));
    flushMicrotasks();

    expect(component.tokenSeries()?.id).toBe(7);
  }));

  it('recordDeployment() POSTs /issuance/token-series/:id/smart-contract-deployment', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/1`).flush(proposal({ status: 'LAUNCHED' }));
    flushMicrotasks();

    const component = fixture.componentInstance;
    component.tokenSeriesIdLookup.set('1');
    component.loadTokenSeriesById();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/token-series/1`).flush(tokenSeries());
    flushMicrotasks();

    component.deploymentBytecodeHash.set('0xhash');
    component.deploymentVersion.set('v1');
    component.recordDeployment();

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/token-series/1/smart-contract-deployment`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ bytecode_hash: '0xhash', version: 'v1' });
    req.flush(tokenSeries({ smart_contract_deployment_id: 9 }));
    flushMicrotasks();

    expect(component.tokenSeries()?.smart_contract_deployment_id).toBe(9);
  }));
});
