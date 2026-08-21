import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { environment } from '../../../environments/environment';
import { Custodian, CustodianListResponse } from './custodian.models';
import { CustodianService } from './custodian.service';

function custodian(overrides: Partial<Custodian> = {}): Custodian {
  return {
    id: 1,
    name: 'GIFT Custody Partners',
    ifsca_registration_no: 'IFSCA/CUST/0001',
    ifsca_verified: false,
    verified_by_user_id: null,
    verified_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function custodianListResponse(items: Custodian[]): CustodianListResponse {
  return { total: items.length, items };
}

describe('CustodianService', () => {
  let service: CustodianService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(CustodianService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('starts with an empty custodian list', () => {
    expect(service.custodians()).toEqual([]);
    expect(service.verifiedCustodians()).toEqual([]);
  });

  it('list() GETs /custodians and stores the unwrapped items', async () => {
    const promise = service.list();
    const req = httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/custodians`);
    expect(req.request.method).toBe('GET');
    req.flush(custodianListResponse([custodian({ id: 1, ifsca_verified: true }), custodian({ id: 2, ifsca_verified: false })]));

    const result = await promise;
    expect(result.length).toBe(2);
    expect(service.custodians().length).toBe(2);
    expect(service.verifiedCustodians()).toEqual([custodian({ id: 1, ifsca_verified: true })]);
  });

  it('create() POSTs /custodians and appends the response', async () => {
    const promise = service.create({ name: 'GIFT Custody Partners', ifsca_registration_no: 'IFSCA/CUST/0001' });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/custodians`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ name: 'GIFT Custody Partners', ifsca_registration_no: 'IFSCA/CUST/0001' });
    req.flush(custodian());

    const result = await promise;
    expect(result.id).toBe(1);
    expect(service.custodians().length).toBe(1);
  });

  it('verify() posts to /custodians/:id/verify and replaces the row in place', async () => {
    const promise = service.list();
    httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/custodians`).flush(custodianListResponse([custodian({ id: 1, ifsca_verified: false })]));
    await promise;

    const verifyPromise = service.verify(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/custodians/1/verify`);
    expect(req.request.method).toBe('POST');
    req.flush(custodian({ id: 1, ifsca_verified: true }));

    const result = await verifyPromise;
    expect(result.ifsca_verified).toBeTrue();
    expect(service.custodians()[0].ifsca_verified).toBeTrue();
  });

  it('has no unverify method -- verification is one-directional in the real backend', () => {
    expect((service as unknown as { unverify?: unknown }).unverify).toBeUndefined();
  });
});
