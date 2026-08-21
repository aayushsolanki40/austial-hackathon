import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { environment } from '../../../../environments/environment';
import { KycReviewQueueItem, KycReviewQueueResponse } from '../admin.models';
import KycReviewQueueComponent from './kyc-review-queue.component';

function item(overrides: Partial<KycReviewQueueItem> = {}): KycReviewQueueItem {
  return {
    id: 1,
    investor_id: 7,
    status: 'MANUAL_REVIEW',
    legal_name: 'Jane Doe',
    date_of_birth: '1990-01-01',
    nationality: 'IN',
    submitted_at: '2026-01-01T00:00:00Z',
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

function queueResponse(items: KycReviewQueueItem[]): KycReviewQueueResponse {
  return { total: items.length, items };
}

describe('KycReviewQueueComponent', () => {
  let fixture: ComponentFixture<KycReviewQueueComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KycReviewQueueComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(KycReviewQueueComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('lists queue items returned by GET /kyc/review-queue', () => {
    fixture.detectChanges();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/kyc/review-queue?skip=0&take=50`);
    expect(req.request.method).toBe('GET');
    req.flush(queueResponse([item()]));
    fixture.detectChanges();

    expect(fixture.componentInstance.state()).toBe('loaded');
    expect(fixture.componentInstance.queue().length).toBe(1);
  });

  it('falls back to the error state when the endpoint is unavailable', () => {
    fixture.detectChanges();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/kyc/review-queue?skip=0&take=50`);
    req.flush('not found', { status: 404, statusText: 'Not Found' });
    fixture.detectChanges();

    expect(fixture.componentInstance.state()).toBe('error');
  });

  it('approve() posts to /kyc/submissions/{id}/approve and removes the row from the queue', () => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/kyc/review-queue?skip=0&take=50`).flush(queueResponse([item()]));
    fixture.detectChanges();

    fixture.componentInstance.approve(item());
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/kyc/submissions/1/approve`);
    expect(req.request.method).toBe('POST');
    req.flush({});

    expect(fixture.componentInstance.queue().length).toBe(0);
  });

  it('reject() posts the typed reason to /kyc/submissions/{id}/reject and removes the row', () => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/kyc/review-queue?skip=0&take=50`).flush(queueResponse([item()]));
    fixture.detectChanges();

    fixture.componentInstance.setReason(1, 'Document unclear');
    fixture.componentInstance.reject(item());
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/kyc/submissions/1/reject`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ reason: 'Document unclear' });
    req.flush({});

    expect(fixture.componentInstance.queue().length).toBe(0);
  });

  it('reject() does nothing without a reason', () => {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/kyc/review-queue?skip=0&take=50`).flush(queueResponse([item()]));
    fixture.detectChanges();

    fixture.componentInstance.reject(item());
    httpMock.expectNone(`${environment.apiBaseUrl}/kyc/submissions/1/reject`);
    expect(fixture.componentInstance.queue().length).toBe(1);
  });
});
