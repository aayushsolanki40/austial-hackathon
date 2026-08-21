import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { environment } from '../../../../environments/environment';
import { Custodian } from '../../../core/custodian/custodian.models';
import { AdminIssuerListItem } from '../admin.models';
import IssuerCustodianAdminComponent from './issuer-custodian-admin.component';

function custodian(overrides: Partial<Custodian> = {}): Custodian {
  return {
    id: 1,
    name: 'GIFT Custody Partners',
    ifsca_registration_no: 'IFSCA/CUST/0001',
    jurisdiction: 'IN',
    ifsca_verified: false,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function issuer(overrides: Partial<AdminIssuerListItem> = {}): AdminIssuerListItem {
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

  it('lists custodians returned by GET /custodians', async () => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/custodians`).flush([custodian()]);
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers`).flush([]);
    // `CustodianService.list()` resolves via a Promise (`firstValueFrom`), unlike
    // `loadIssuers()`'s direct `Observable.subscribe()` -- its `.then()` continuation is a
    // microtask that needs an explicit flush before `custodianState()` reflects it.
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.custodianState()).toBe('loaded');
    expect(fixture.componentInstance.custodians().length).toBe(1);
  });

  it('lists issuers returned by GET /issuers', () => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/custodians`).flush([]);
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers`).flush([issuer()]);
    fixture.detectChanges();

    expect(fixture.componentInstance.issuerState()).toBe('loaded');
    expect(fixture.componentInstance.issuers().length).toBe(1);
  });

  it('falls back to the error state when /custodians is unavailable', async () => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/custodians`).flush('not found', { status: 404, statusText: 'Not Found' });
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers`).flush([]);
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.custodianState()).toBe('error');
  });

  it('falls back to the error state when /issuers is unavailable (module not shipped yet)', () => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/custodians`).flush([]);
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers`).flush('not found', { status: 404, statusText: 'Not Found' });
    fixture.detectChanges();

    expect(fixture.componentInstance.issuerState()).toBe('error');
  });

  it('toggleVerification() posts to /custodians/:id/verify when currently unverified', async () => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/custodians`).flush([custodian({ ifsca_verified: false })]);
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers`).flush([]);
    fixture.detectChanges();

    const promise = fixture.componentInstance.toggleVerification(1, false);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/custodians/1/verify`);
    expect(req.request.method).toBe('POST');
    req.flush(custodian({ ifsca_verified: true }));
    await promise;

    expect(fixture.componentInstance.custodians()[0].ifsca_verified).toBeTrue();
  });

  it('toggleVerification() posts to /custodians/:id/unverify when currently verified', async () => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/custodians`).flush([custodian({ ifsca_verified: true })]);
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers`).flush([]);
    fixture.detectChanges();

    const promise = fixture.componentInstance.toggleVerification(1, true);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/custodians/1/unverify`);
    expect(req.request.method).toBe('POST');
    req.flush(custodian({ ifsca_verified: false }));
    await promise;

    expect(fixture.componentInstance.custodians()[0].ifsca_verified).toBeFalse();
  });

  it('createCustodian() POSTs /custodians with the form values', async () => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/custodians`).flush([]);
    httpMock.expectOne(`${environment.apiBaseUrl}/issuers`).flush([]);
    fixture.detectChanges();

    const component = fixture.componentInstance;
    component.createCustodianForm.setValue({
      name: 'GIFT Custody Partners',
      ifsca_registration_no: 'IFSCA/CUST/0001',
      jurisdiction: 'IN',
    });
    const promise = component.createCustodian();

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/custodians`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ name: 'GIFT Custody Partners', ifsca_registration_no: 'IFSCA/CUST/0001', jurisdiction: 'IN' });
    req.flush(custodian());
    await promise;

    expect(component.custodians().length).toBe(1);
  });
});
