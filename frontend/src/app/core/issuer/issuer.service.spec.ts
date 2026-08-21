import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { environment } from '../../../environments/environment';
import { Asset, AssetListResponse, IssuerProfile } from './issuer.models';
import { IssuerService } from './issuer.service';

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

describe('IssuerService', () => {
  let service: IssuerService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(IssuerService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('starts with no profile and no assets', () => {
    expect(service.profile()).toBeNull();
    expect(service.assets()).toEqual([]);
  });

  it('fetchProfile() stores the returned profile', async () => {
    const promise = service.fetchProfile();
    const req = httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/issuers/profile`);
    expect(req.request.method).toBe('GET');
    req.flush(issuerProfile());

    const result = await promise;
    expect(result?.legal_name).toBe('Acme Real Estate LLC');
    expect(service.profile()?.id).toBe(1);
  });

  it('fetchProfile() treats a failed request (e.g. 404, no profile yet) as no profile', async () => {
    const promise = service.fetchProfile();
    httpMock
      .expectOne((r) => r.url === `${environment.apiBaseUrl}/issuers/profile`)
      .flush('not found', { status: 404, statusText: 'Not Found' });

    const result = await promise;
    expect(result).toBeNull();
    expect(service.profile()).toBeNull();
  });

  it('createProfile() POSTs /issuers/profile and stores the response', async () => {
    const promise = service.createProfile({
      legal_name: 'Acme Real Estate LLC',
      registration_number: 'REG-001',
      registration_jurisdiction: 'IN',
    });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuers/profile`);
    expect(req.request.method).toBe('POST');
    req.flush(issuerProfile());

    const result = await promise;
    expect(result.id).toBe(1);
    expect(service.profile()?.legal_name).toBe('Acme Real Estate LLC');
  });

  it('listAssets() GETs /assets and stores the unwrapped items', async () => {
    const promise = service.listAssets();
    const req = httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/assets`);
    expect(req.request.method).toBe('GET');
    req.flush(assetListResponse([asset()]));

    const result = await promise;
    expect(result.length).toBe(1);
    expect(service.assets()[0].name).toBe('Mumbai Commercial Tower');
  });

  it('createAsset() POSTs /assets with just name/asset_class/description and prepends the response', async () => {
    const promise = service.createAsset({
      name: 'Mumbai Commercial Tower',
      asset_class: 'REAL_ESTATE',
      description: 'A commercial office tower.',
    });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/assets`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      name: 'Mumbai Commercial Tower',
      asset_class: 'REAL_ESTATE',
      description: 'A commercial office tower.',
    });
    req.flush(asset());

    const result = await promise;
    expect(result.id).toBe(1);
    expect(service.assets().length).toBe(1);
  });

  it('attachCustodian() POSTs /assets/:id/custodian and replaces the row in place', async () => {
    const listPromise = service.listAssets();
    httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/assets`).flush(assetListResponse([asset()]));
    await listPromise;

    const promise = service.attachCustodian(1, 7);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/assets/1/custodian`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ custodian_id: 7 });
    req.flush(asset({ custodian_id: 7, custodian_verified: true, tokenization_ready: true }));

    const result = await promise;
    expect(result.tokenization_ready).toBeTrue();
    expect(service.assets()[0].tokenization_ready).toBeTrue();
  });
});
