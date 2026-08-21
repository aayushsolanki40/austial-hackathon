import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { Subscription } from './subscriptions.models';
import { IN_FLIGHT_SUBSCRIPTION_STATUSES, SubscriptionsService } from './subscriptions.service';

function subscription(overrides: Partial<Subscription> = {}): Subscription {
  return {
    id: 1,
    investor_id: 1,
    token_series_id: 1,
    symbol: 'MCT',
    units: 10,
    amount_usd: 1000,
    allocated_units: null,
    status: 'PENDING',
    risk_disclosure_accepted: true,
    fee_disclosure_accepted: true,
    disclosures_acknowledged_at: '2026-01-01T00:00:00Z',
    processed_by_user_id: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('SubscriptionsService', () => {
  let service: SubscriptionsService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(SubscriptionsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('starts with no subscriptions and no current subscription', () => {
    expect(service.mySubscriptions()).toEqual([]);
    expect(service.current()).toBeNull();
  });

  it('create() POSTs /subscriptions with the request body and stores the result', async () => {
    const promise = service.create({
      token_series_id: 1,
      units: 10,
      risk_disclosure_accepted: true,
      fee_disclosure_accepted: true,
    });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/subscriptions`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      token_series_id: 1,
      units: 10,
      risk_disclosure_accepted: true,
      fee_disclosure_accepted: true,
    });
    req.flush(subscription());

    const result = await promise;
    expect(result.status).toBe('PENDING');
    expect(service.current()?.id).toBe(1);
    expect(service.mySubscriptions()[0].id).toBe(1);
  });

  it('listMine() GETs /subscriptions/mine and stores items', async () => {
    const promise = service.listMine();
    const req = httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/subscriptions/mine`);
    expect(req.request.method).toBe('GET');
    req.flush({ total: 1, items: [subscription()] });

    const result = await promise;
    expect(result.length).toBe(1);
    expect(service.mySubscriptions()[0].symbol).toBe('MCT');
  });

  it('fetchMine() GETs /subscriptions/mine/:id and sets current', async () => {
    const promise = service.fetchMine(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/subscriptions/mine/1`);
    expect(req.request.method).toBe('GET');
    req.flush(subscription({ status: 'CONFIRMED' }));

    const result = await promise;
    expect(result.status).toBe('CONFIRMED');
    expect(service.current()?.status).toBe('CONFIRMED');
  });

  it('cancel() POSTs /subscriptions/mine/:id/cancel and patches the subscription in place', async () => {
    const listPromise = service.listMine();
    httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/subscriptions/mine`).flush({ total: 1, items: [subscription()] });
    await listPromise;

    const cancelPromise = service.cancel(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/subscriptions/mine/1/cancel`);
    expect(req.request.method).toBe('POST');
    req.flush(subscription({ status: 'CANCELLED' }));

    await cancelPromise;
    expect(service.mySubscriptions()[0].status).toBe('CANCELLED');
  });

  it('IN_FLIGHT_SUBSCRIPTION_STATUSES covers exactly PENDING/FUNDED/CONFIRMED', () => {
    expect(IN_FLIGHT_SUBSCRIPTION_STATUSES).toEqual(['PENDING', 'FUNDED', 'CONFIRMED']);
  });
});
