import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { environment } from '../../../../environments/environment';
import { Custodian, CustodianListResponse } from '../../../core/custodian/custodian.models';
import { AdminIssuerListItem, IssuerReviewQueueResponse } from '../admin.models';
import IssuerCustodianAdminComponent from './issuer-custodian-admin.component';

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

function issuer(overrides: Partial<AdminIssuerListItem> = {}): AdminIssuerListItem {
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

function issuerQueueResponse(items: AdminIssuerListItem[]): IssuerReviewQueueResponse {
  return { total: items.length, items };
}

describe('IssuerCustodianAdminComponent', () => {
  let fixture: ComponentFixture<IssuerCustodianAdminComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IssuerCustodianAdminComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(IssuerCustodianAdminComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function expectCustodiansReq() {
    return httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/custodians`);
  }

  function expectIssuerQueueReq() {
    return httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/issuers/review-queue`);
  }

  it('lists custodians returned by GET /custodians', async () => {
    fixture.detectChanges();
    expectCustodiansReq().flush(custodianListResponse([custodian()]));
    expectIssuerQueueReq().flush(issuerQueueResponse([]));
    // `CustodianService.list()` resolves via a Promise (`firstValueFrom`), unlike
    // `loadIssuerQueue()`'s direct `Observable.subscribe()` -- its `.then()` continuation is
    // a microtask that needs an explicit flush before `custodianState()` reflects it.
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.custodianState()).toBe('loaded');
    expect(fixture.componentInstance.custodians().length).toBe(1);
  });

  it('lists issuers pending review from GET /issuers/review-queue', () => {
    fixture.detectChanges();
    expectCustodiansReq().flush(custodianListResponse([]));
    expectIssuerQueueReq().flush(issuerQueueResponse([issuer()]));
    fixture.detectChanges();

    expect(fixture.componentInstance.issuerState()).toBe('loaded');
    expect(fixture.componentInstance.issuerQueue().length).toBe(1);
  });

  it('falls back to the error state when /custodians is unavailable', async () => {
    fixture.detectChanges();
    expectCustodiansReq().flush('not found', { status: 404, statusText: 'Not Found' });
    expectIssuerQueueReq().flush(issuerQueueResponse([]));
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.custodianState()).toBe('error');
  });

  it('falls back to the error state when /issuers/review-queue is unavailable', () => {
    fixture.detectChanges();
    expectCustodiansReq().flush(custodianListResponse([]));
    expectIssuerQueueReq().flush('forbidden', { status: 403, statusText: 'Forbidden' });
    fixture.detectChanges();

    expect(fixture.componentInstance.issuerState()).toBe('error');
  });

  it('verifyCustodian() posts to /custodians/:id/verify', async () => {
    fixture.detectChanges();
    expectCustodiansReq().flush(custodianListResponse([custodian({ ifsca_verified: false })]));
    expectIssuerQueueReq().flush(issuerQueueResponse([]));
    fixture.detectChanges();

    const promise = fixture.componentInstance.verifyCustodian(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/custodians/1/verify`);
    expect(req.request.method).toBe('POST');
    req.flush(custodian({ ifsca_verified: true }));
    await promise;

    expect(fixture.componentInstance.custodians()[0].ifsca_verified).toBeTrue();
  });

  it('has no unverify affordance -- verification is one-directional in the real backend', () => {
    expect((fixture.componentInstance as unknown as { toggleVerification?: unknown }).toggleVerification).toBeUndefined();
  });

  it('createCustodian() POSTs /custodians with the form values', async () => {
    fixture.detectChanges();
    expectCustodiansReq().flush(custodianListResponse([]));
    expectIssuerQueueReq().flush(issuerQueueResponse([]));
    fixture.detectChanges();

    const component = fixture.componentInstance;
    component.createCustodianForm.setValue({
      name: 'GIFT Custody Partners',
      ifsca_registration_no: 'IFSCA/CUST/0001',
    });
    const promise = component.createCustodian();

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/custodians`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ name: 'GIFT Custody Partners', ifsca_registration_no: 'IFSCA/CUST/0001' });
    req.flush(custodian());
    await promise;

    expect(component.custodians().length).toBe(1);
  });

  it('approveIssuer() POSTs /issuers/:id/approve and removes the issuer from the queue', () => {
    fixture.detectChanges();
    expectCustodiansReq().flush(custodianListResponse([]));
    expectIssuerQueueReq().flush(issuerQueueResponse([issuer()]));
    fixture.detectChanges();

    const component = fixture.componentInstance;
    component.approveIssuer(issuer());
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuers/1/approve`);
    expect(req.request.method).toBe('POST');
    req.flush(issuer({ verification_status: 'VERIFIED' }));

    expect(component.issuerQueue().length).toBe(0);
  });

  it('rejectIssuer() POSTs /issuers/:id/reject with the entered reason and removes the issuer from the queue', () => {
    fixture.detectChanges();
    expectCustodiansReq().flush(custodianListResponse([]));
    expectIssuerQueueReq().flush(issuerQueueResponse([issuer()]));
    fixture.detectChanges();

    const component = fixture.componentInstance;
    component.setReason(1, 'Registration number could not be verified.');
    component.rejectIssuer(issuer());

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuers/1/reject`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ reason: 'Registration number could not be verified.' });
    req.flush(issuer({ verification_status: 'REJECTED', rejection_reason: 'Registration number could not be verified.' }));

    expect(component.issuerQueue().length).toBe(0);
  });

  it('rejectIssuer() is a no-op when no reason has been entered', () => {
    fixture.detectChanges();
    expectCustodiansReq().flush(custodianListResponse([]));
    expectIssuerQueueReq().flush(issuerQueueResponse([issuer()]));
    fixture.detectChanges();

    fixture.componentInstance.rejectIssuer(issuer());

    httpMock.expectNone(`${environment.apiBaseUrl}/issuers/1/reject`);
    expect(fixture.componentInstance.issuerQueue().length).toBe(1);
  });
});
