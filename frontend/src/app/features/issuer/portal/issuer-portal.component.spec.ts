import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';

import { environment } from '../../../../environments/environment';
import { Asset, IssuerProfile } from '../../../core/issuer/issuer.models';
import { Custodian } from '../../../core/custodian/custodian.models';
import IssuerPortalComponent from './issuer-portal.component';

function issuerProfile(overrides: Partial<IssuerProfile> = {}): IssuerProfile {
  return {
    id: 1,
    legal_name: 'Acme Real Estate LLC',
    registration_number: 'REG-001',
    jurisdiction: 'IN',
    contact_email: 'issuer-contact@example.test',
    verification_status: 'PENDING',
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
    jurisdiction: 'IN',
    ifsca_verified: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function asset(overrides: Partial<Asset> = {}): Asset {
  return {
    id: 1,
    issuer_id: 1,
    custodian_id: 1,
    name: 'Mumbai Commercial Tower',
    asset_class: 'REAL_ESTATE',
    description: 'A commercial office tower.',
    valuation_amount: 5_000_000,
    valuation_currency: 'USD',
    class_attributes: { property_location: 'Mumbai, IN', valuation_basis: 'Independent appraisal' },
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('IssuerPortalComponent', () => {
  let fixture: ComponentFixture<IssuerPortalComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IssuerPortalComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(IssuerPortalComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

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
      jurisdiction: 'IN',
      contact_email: 'issuer-contact@example.test',
    });
    component.submitProfile();

    const postReq = httpMock.expectOne(`${environment.apiBaseUrl}/issuers/profile`);
    expect(postReq.request.method).toBe('POST');
    postReq.flush(issuerProfile());
    flushMicrotasks();

    httpMock.expectOne(`${environment.apiBaseUrl}/assets`).flush([]);
    httpMock.expectOne(`${environment.apiBaseUrl}/custodians`).flush([custodian()]);
    flushMicrotasks();

    expect(component.viewState()).toBe('profile');
    expect(component.profile()?.legal_name).toBe('Acme Real Estate LLC');
  }));

  it('loads assets/custodians and lists them when a profile already exists', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers/profile`).flush(issuerProfile());
    flushMicrotasks();

    httpMock.expectOne(`${environment.apiBaseUrl}/assets`).flush([asset()]);
    httpMock.expectOne(`${environment.apiBaseUrl}/custodians`).flush([custodian({ ifsca_verified: true }), custodian({ id: 2, ifsca_verified: false })]);
    flushMicrotasks();

    const component = fixture.componentInstance;
    expect(component.viewState()).toBe('profile');
    expect(component.assets().length).toBe(1);
    expect(component.verifiedCustodians().length).toBe(1);
  }));

  it('submitAsset() sends class_attributes for the selected asset class', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers/profile`).flush(issuerProfile());
    flushMicrotasks();
    httpMock.expectOne(`${environment.apiBaseUrl}/assets`).flush([]);
    httpMock.expectOne(`${environment.apiBaseUrl}/custodians`).flush([custodian()]);
    flushMicrotasks();

    const component = fixture.componentInstance;
    component.onAssetClassChange('REAL_ESTATE');
    component.setClassAttribute('property_location', { target: { value: 'Mumbai, IN' } } as unknown as Event);
    component.setClassAttribute('valuation_basis', { target: { value: 'Independent appraisal' } } as unknown as Event);

    component.assetForm.setValue({
      name: 'Mumbai Commercial Tower',
      description: 'A commercial office tower.',
      asset_class: 'REAL_ESTATE',
      custodian_id: 1,
      valuation_amount: 5_000_000,
      valuation_currency: 'USD',
    });
    component.submitAsset();

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/assets`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body.class_attributes).toEqual({
      property_location: 'Mumbai, IN',
      valuation_basis: 'Independent appraisal',
    });
    req.flush(asset());
    flushMicrotasks();

    expect(component.assets().length).toBe(1);
  }));

  it('submitAsset() is blocked while a required dynamic field is missing', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers/profile`).flush(issuerProfile());
    flushMicrotasks();
    httpMock.expectOne(`${environment.apiBaseUrl}/assets`).flush([]);
    httpMock.expectOne(`${environment.apiBaseUrl}/custodians`).flush([custodian()]);
    flushMicrotasks();

    const component = fixture.componentInstance;
    component.onAssetClassChange('REAL_ESTATE');
    component.assetForm.setValue({
      name: 'Mumbai Commercial Tower',
      description: 'A commercial office tower.',
      asset_class: 'REAL_ESTATE',
      custodian_id: 1,
      valuation_amount: 5_000_000,
      valuation_currency: 'USD',
    });
    component.submitAsset();

    httpMock.expectNone(`${environment.apiBaseUrl}/assets`);
    expect(component.assets().length).toBe(0);
  }));
});
