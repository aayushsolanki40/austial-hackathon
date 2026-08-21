import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { environment } from '../../../../environments/environment';
import { ProposalDetail } from '../../../core/issuance/issuance.models';
import ProposalDetailComponent from './proposal-detail.component';

function proposal(overrides: Partial<ProposalDetail> = {}): ProposalDetail {
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
    disclosures: [],
    missing_disclosure_types: ['RISK', 'FEE', 'LIQUIDITY', 'CUSTODY', 'TAX', 'PROSPECTUS'],
    disclosures_complete: false,
    ...overrides,
  };
}

describe('ProposalDetailComponent', () => {
  let fixture: ComponentFixture<ProposalDetailComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProposalDetailComponent],
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

    fixture = TestBed.createComponent(ProposalDetailComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('loads the proposal by id from the route via /issuance/proposals/mine/:id', fakeAsync(() => {
    fixture.detectChanges();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1`);
    expect(req.request.method).toBe('GET');
    req.flush(proposal());
    flushMicrotasks();

    expect(fixture.componentInstance.state()).toBe('loaded');
    expect(fixture.componentInstance.proposal()?.id).toBe(1);
  }));

  it('allows submit-for-review only while DRAFT', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1`).flush(proposal({ status: 'DRAFT' }));
    flushMicrotasks();
    expect(fixture.componentInstance.canSubmitForReview()).toBeTrue();

    fixture.componentInstance.load();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1`).flush(proposal({ status: 'DOCUMENTATION_REVIEW' }));
    flushMicrotasks();
    expect(fixture.componentInstance.canSubmitForReview()).toBeFalse();
  }));

  it('submitForReview() POSTs /issuance/proposals/mine/:id/submit', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1`).flush(proposal({ status: 'DRAFT' }));
    flushMicrotasks();

    fixture.componentInstance.submitForReview();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1/submit`);
    expect(req.request.method).toBe('POST');
    req.flush(proposal({ status: 'DOCUMENTATION_REVIEW' }));
    flushMicrotasks();

    expect(fixture.componentInstance.proposal()?.status).toBe('DOCUMENTATION_REVIEW');
  }));

  it('disclosures are editable while status is not LAUNCHED/REJECTED', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1`).flush(proposal({ status: 'IFSCA_APPROVED' }));
    flushMicrotasks();
    expect(fixture.componentInstance.disclosuresEditable()).toBeTrue();

    fixture.componentInstance.load();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1`).flush(proposal({ status: 'LAUNCHED' }));
    flushMicrotasks();
    expect(fixture.componentInstance.disclosuresEditable()).toBeFalse();
  }));
});
