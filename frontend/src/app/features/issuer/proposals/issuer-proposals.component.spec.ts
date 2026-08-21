import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { environment } from '../../../../environments/environment';
import { Asset, AssetListResponse } from '../../../core/issuer/issuer.models';
import { ProposalDetail, ProposalListResponse, TokenizationProposal } from '../../../core/issuance/issuance.models';
import IssuerProposalsComponent from './issuer-proposals.component';

function asset(overrides: Partial<Asset> = {}): Asset {
  return {
    id: 1,
    issuer_id: 1,
    custodian_id: 7,
    name: 'Mumbai Commercial Tower',
    asset_class: 'REAL_ESTATE',
    description: 'A commercial office tower.',
    custodian_verified: true,
    tokenization_ready: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function assetListResponse(items: Asset[]): AssetListResponse {
  return { total: items.length, items };
}

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

describe('IssuerProposalsComponent', () => {
  let fixture: ComponentFixture<IssuerProposalsComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IssuerProposalsComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(IssuerProposalsComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function expectAssetsReq() {
    return httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/assets`);
  }

  function expectProposalsReq() {
    return httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/issuance/proposals/mine`);
  }

  it('loads own assets and proposals on init', fakeAsync(() => {
    fixture.detectChanges();
    expectAssetsReq().flush(assetListResponse([asset()]));
    expectProposalsReq().flush(proposalListResponse([proposal()]));
    flushMicrotasks();

    expect(fixture.componentInstance.loading()).toBeFalse();
    expect(fixture.componentInstance.proposals().length).toBe(1);
  }));

  it('only offers tokenization_ready assets in the create form', fakeAsync(() => {
    fixture.detectChanges();
    expectAssetsReq().flush(assetListResponse([asset({ id: 1, tokenization_ready: true }), asset({ id: 2, tokenization_ready: false })]));
    expectProposalsReq().flush(proposalListResponse([]));
    flushMicrotasks();

    expect(fixture.componentInstance.tokenizationReadyAssets().length).toBe(1);
    expect(fixture.componentInstance.tokenizationReadyAssets()[0].id).toBe(1);
  }));

  it('submitProposal() POSTs /issuance/proposals with the form values', fakeAsync(() => {
    fixture.detectChanges();
    expectAssetsReq().flush(assetListResponse([asset()]));
    expectProposalsReq().flush(proposalListResponse([]));
    flushMicrotasks();

    const component = fixture.componentInstance;
    component.proposalForm.setValue({
      asset_id: 1,
      total_units: 10000,
      unit_price_usd: 100,
      min_subscription_units: 10,
      subscription_start_at: '2026-09-01',
      subscription_end_at: '2026-09-30',
    });
    component.submitProposal();

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      asset_id: 1,
      total_units: 10000,
      unit_price_usd: 100,
      min_subscription_units: 10,
      subscription_start_at: '2026-09-01',
      subscription_end_at: '2026-09-30',
    });
    req.flush(proposalDetail());
    flushMicrotasks();

    expect(component.proposals().length).toBe(1);
  }));

  it('submitProposal() is blocked while the form is invalid', fakeAsync(() => {
    fixture.detectChanges();
    expectAssetsReq().flush(assetListResponse([asset()]));
    expectProposalsReq().flush(proposalListResponse([]));
    flushMicrotasks();

    fixture.componentInstance.submitProposal();

    httpMock.expectNone(`${environment.apiBaseUrl}/issuance/proposals`);
    expect(fixture.componentInstance.proposals().length).toBe(0);
  }));
});
