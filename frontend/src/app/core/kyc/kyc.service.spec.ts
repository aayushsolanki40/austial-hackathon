import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { environment } from '../../../environments/environment';
import { InvestorProfile, KycSubmission } from './kyc.models';
import { KycService } from './kyc.service';

function profile(overrides: Partial<InvestorProfile> = {}): InvestorProfile {
  return {
    id: 1,
    investor_type: 'INDIVIDUAL',
    jurisdiction: 'IN',
    risk_profile: 'MODERATE',
    kyc_status: 'PENDING',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function submission(overrides: Partial<KycSubmission> = {}): KycSubmission {
  return {
    id: 1,
    investor_id: 1,
    status: 'DRAFT',
    legal_name: 'Jane Doe',
    date_of_birth: '1990-01-01',
    nationality: 'IN',
    submitted_at: null,
    screening_result: null,
    reviewed_by_user_id: null,
    review_notes: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    documents: [],
    consent: null,
    ...overrides,
  };
}

describe('KycService', () => {
  let service: KycService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(KycService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('starts with no profile/submission and a null kycStatus', () => {
    expect(service.profile()).toBeNull();
    expect(service.submission()).toBeNull();
    expect(service.kycStatus()).toBeNull();
    expect(service.isVerified()).toBeFalse();
  });

  it('fetchProfile() stores the returned profile and updates derived signals', async () => {
    const promise = service.fetchProfile();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/investors/profile`);
    expect(req.request.method).toBe('GET');
    req.flush(profile({ kyc_status: 'VERIFIED' }));

    const result = await promise;

    expect(result?.kyc_status).toBe('VERIFIED');
    expect(service.isVerified()).toBeTrue();
    expect(service.isInReview()).toBeFalse();
  });

  it('fetchProfile() treats a failed request (e.g. 404, no profile yet) as no profile', async () => {
    const promise = service.fetchProfile();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/investors/profile`);
    req.flush('not found', { status: 404, statusText: 'Not Found' });

    const result = await promise;

    expect(result).toBeNull();
    expect(service.profile()).toBeNull();
    expect(service.isVerified()).toBeFalse();
  });

  it('isInReview() is true for PENDING', async () => {
    const promise = service.fetchProfile();
    httpMock.expectOne(`${environment.apiBaseUrl}/investors/profile`).flush(profile({ kyc_status: 'PENDING' }));
    await promise;

    expect(service.isInReview()).toBeTrue();
    expect(service.isVerified()).toBeFalse();
    expect(service.isRejected()).toBeFalse();
  });

  it('createProfile() POSTs /investors/profile and stores the response', async () => {
    const promise = service.createProfile({ investor_type: 'INDIVIDUAL', jurisdiction: 'IN', risk_profile: 'MODERATE' });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/investors/profile`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ investor_type: 'INDIVIDUAL', jurisdiction: 'IN', risk_profile: 'MODERATE' });
    req.flush(profile());

    const result = await promise;
    expect(result.investor_type).toBe('INDIVIDUAL');
    expect(service.profile()?.id).toBe(1);
  });

  it('createSubmission() POSTs /kyc/submissions and stores the response', async () => {
    const promise = service.createSubmission({ legal_name: 'Jane Doe', date_of_birth: '1990-01-01', nationality: 'IN' });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/kyc/submissions`);
    expect(req.request.method).toBe('POST');
    req.flush(submission());

    const result = await promise;
    expect(result.status).toBe('DRAFT');
    expect(service.submission()?.id).toBe(1);
  });

  it('fetchLatestSubmission() GETs /kyc/submissions and stores the first (newest) item', async () => {
    const promise = service.fetchLatestSubmission();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/kyc/submissions`);
    expect(req.request.method).toBe('GET');
    req.flush([submission({ id: 2 }), submission({ id: 1 })]);

    const result = await promise;
    expect(result?.id).toBe(2);
    expect(service.submission()?.id).toBe(2);
  });

  it('fetchLatestSubmission() returns null when the investor has no submissions yet', async () => {
    const promise = service.fetchLatestSubmission();
    httpMock.expectOne(`${environment.apiBaseUrl}/kyc/submissions`).flush([]);

    const result = await promise;
    expect(result).toBeNull();
  });

  it('requestDocumentUpload() posts to /kyc/submissions/:id/documents/upload-url', async () => {
    const promise = service.requestDocumentUpload(1, { document_type: 'PASSPORT', content_type: 'image/png' });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/kyc/submissions/1/documents/upload-url`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ document_type: 'PASSPORT', content_type: 'image/png' });
    req.flush({ upload_url: 'https://s3.example.com/obj', object_key: 'kyc/1/1/passport/abc' });

    const result = await promise;
    expect(result.object_key).toBe('kyc/1/1/passport/abc');
  });

  it('confirmDocumentUpload() posts to /kyc/submissions/:id/documents', async () => {
    const promise = service.confirmDocumentUpload(1, { document_type: 'PASSPORT', object_key: 'kyc/1/1/passport/abc' });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/kyc/submissions/1/documents`);
    expect(req.request.method).toBe('POST');
    req.flush({ id: 1, document_type: 'PASSPORT', object_key: 'kyc/1/1/passport/abc', ocr_result: null, created_at: '2026-01-01T00:00:00Z' });

    const result = await promise;
    expect(result.document_type).toBe('PASSPORT');
  });

  it('submitConsent() posts the disclosure_version to /kyc/submissions/:id/consent', async () => {
    const promise = service.submitConsent(1, 'v1');
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/kyc/submissions/1/consent`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ disclosure_version: 'v1' });
    req.flush({ id: 1, submission_id: 1, disclosure_version: 'v1', acknowledged_at: '2026-01-01T00:00:00Z' });

    const result = await promise;
    expect(result.id).toBe(1);
  });

  // Two sequential HTTP calls chained inside the service (`submit` then `fetchProfile`) --
  // `fakeAsync`/`tick()` deterministically drains the microtask queue between each
  // `flush()` so the second request has actually been issued before we assert on it,
  // unlike a bare `async`/`await` test where nothing forces that ordering.
  it('submit() posts to /kyc/submissions/:id/submit and refetches the profile', fakeAsync(() => {
    let result: Awaited<ReturnType<KycService['submit']>> | undefined;
    service.submit(1).then((value) => (result = value));

    const submitReq = httpMock.expectOne(`${environment.apiBaseUrl}/kyc/submissions/1/submit`);
    expect(submitReq.request.method).toBe('POST');
    submitReq.flush(submission({ status: 'MANUAL_REVIEW' }));
    tick();

    const fetchReq = httpMock.expectOne(`${environment.apiBaseUrl}/investors/profile`);
    fetchReq.flush(profile({ kyc_status: 'PENDING' }));
    tick();

    expect(result?.status).toBe('MANUAL_REVIEW');
    expect(service.submission()?.status).toBe('MANUAL_REVIEW');
  }));
});
