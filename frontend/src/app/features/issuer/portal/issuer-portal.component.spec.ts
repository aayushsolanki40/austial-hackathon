import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { environment } from '../../../../environments/environment';
import { Asset, AssetListResponse, IssuerProfile } from '../../../core/issuer/issuer.models';
import { Custodian, CustodianListResponse } from '../../../core/custodian/custodian.models';
import IssuerPortalComponent from './issuer-portal.component';

function issuerProfile(overrides: Partial<IssuerProfile> = {}): IssuerProfile {
  return {
    id: 1,
    legal_name: 'Acme Real Estate LLC',
    registration_number: 'REG-001',
    registration_jurisdiction: 'IN',
    verification_status: 'PENDING',
    verified_by_user_id: null,
    verified_at: null,
    rejection_reason: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function custodian(overrides: Partial<Custodian> = {}): Custodian {
  return {
    id: 1,
    name: 'GIFT Custody Partners',
    ifsca_registration_no: 'IFSCA/CUST/0001',
    ifsca_verified: true,
    verified_by_user_id: 9,
    verified_at: '2026-01-01T00:00:00Z',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function asset(overrides: Partial<Asset> = {}): Asset {
  return {
    id: 1,
    issuer_id: 1,
    custodian_id: null,
    name: 'Mumbai Commercial Tower',
    asset_class: 'REAL_ESTATE',
    description: 'A commercial office tower.',
    custodian_verified: false,
    tokenization_ready: false,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function assetListResponse(items: Asset[]): AssetListResponse {
  return { total: items.length, items };
}

function custodianListResponse(items: Custodian[]): CustodianListResponse {
  return { total: items.length, items };
}

describe('IssuerPortalComponent', () => {
  let fixture: ComponentFixture<IssuerPortalComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IssuerPortalComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(IssuerPortalComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function expectAssetsReq() {
    return httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/assets`);
  }

  function expectCustodiansReq() {
    return httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/custodians`);
  }

  it('shows the create-profile form when the issuer has no profile yet', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers/profile`).flush('not found', { status: 404, statusText: 'Not Found' });
    flushMicrotasks();

    expect(fixture.componentInstance.viewState()).toBe('create-profile');
  }));

  it('submitProfile() POSTs /issuers/profile then loads assets and custodians', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers/profile`).flush('not found', { status: 404, statusText: 'Not Found' });
    flushMicrotasks();

    const component = fixture.componentInstance;
    component.profileForm.setValue({
      legal_name: 'Acme Real Estate LLC',
      registration_number: 'REG-001',
      registration_jurisdiction: 'IN',
    });
    component.submitProfile();

    const postReq = httpMock.expectOne(`${environment.apiBaseUrl}/issuers/profile`);
    expect(postReq.request.method).toBe('POST');
    postReq.flush(issuerProfile());
    flushMicrotasks();

    expectAssetsReq().flush(assetListResponse([]));
    expectCustodiansReq().flush(custodianListResponse([custodian()]));
    flushMicrotasks();

    expect(component.viewState()).toBe('profile');
    expect(component.profile()?.legal_name).toBe('Acme Real Estate LLC');
  }));

  it('loads assets/custodians and lists them when a profile already exists', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers/profile`).flush(issuerProfile());
    flushMicrotasks();

    expectAssetsReq().flush(assetListResponse([asset()]));
    expectCustodiansReq().flush(custodianListResponse([custodian({ ifsca_verified: true }), custodian({ id: 2, ifsca_verified: false })]));
    flushMicrotasks();

    const component = fixture.componentInstance;
    expect(component.viewState()).toBe('profile');
    expect(component.assets().length).toBe(1);
    expect(component.verifiedCustodians().length).toBe(1);
  }));

  it('submitAsset() POSTs /assets with just name/asset_class/description (no class_attributes)', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers/profile`).flush(issuerProfile());
    flushMicrotasks();
    expectAssetsReq().flush(assetListResponse([]));
    expectCustodiansReq().flush(custodianListResponse([custodian()]));
    flushMicrotasks();

    const component = fixture.componentInstance;
    component.onAssetClassChange('REAL_ESTATE');

    component.assetForm.setValue({
      name: 'Mumbai Commercial Tower',
      description: 'A commercial office tower in Mumbai.',
      asset_class: 'REAL_ESTATE',
    });
    component.submitAsset();

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/assets`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      name: 'Mumbai Commercial Tower',
      asset_class: 'REAL_ESTATE',
      description: 'A commercial office tower in Mumbai.',
    });
    req.flush(asset());
    flushMicrotasks();

    expect(component.assets().length).toBe(1);
  }));

  it('submitAsset() is blocked while the form is invalid (e.g. missing description)', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers/profile`).flush(issuerProfile());
    flushMicrotasks();
    expectAssetsReq().flush(assetListResponse([]));
    expectCustodiansReq().flush(custodianListResponse([custodian()]));
    flushMicrotasks();

    const component = fixture.componentInstance;
    component.assetForm.setValue({
      name: 'Mumbai Commercial Tower',
      description: '',
      asset_class: 'REAL_ESTATE',
    });
    component.submitAsset();

    httpMock.expectNone(`${environment.apiBaseUrl}/assets`);
    expect(component.assets().length).toBe(0);
  }));

  it('attachCustodian() POSTs /assets/:id/custodian for the selected custodian', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers/profile`).flush(issuerProfile());
    flushMicrotasks();
    expectAssetsReq().flush(assetListResponse([asset()]));
    expectCustodiansReq().flush(custodianListResponse([custodian({ id: 7 })]));
    flushMicrotasks();

    const component = fixture.componentInstance;
    component.setAttachCustodianSelection(1, 7);
    component.attachCustodian(component.assets()[0]);

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/assets/1/custodian`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ custodian_id: 7 });
    req.flush(asset({ custodian_id: 7, custodian_verified: true, tokenization_ready: true }));
    flushMicrotasks();

    expect(component.assets()[0].tokenization_ready).toBeTrue();
  }));
});
