import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { Holding } from './holdings.models';
import { HoldingsService } from './holdings.service';

function holding(overrides: Partial<Holding> = {}): Holding {
  return {
    id: 1,
    investor_id: 1,
    subscription_id: 1,
    token_series_id: 1,
    asset_name: 'Mumbai Commercial Tower',
    symbol: 'MCT',
    units: 10,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('HoldingsService', () => {
  let service: HoldingsService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(HoldingsService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('starts with no holdings and no current holding', () => {
    expect(service.myHoldings()).toEqual([]);
    expect(service.current()).toBeNull();
  });

  it('listMine() GETs /holdings/mine and stores items', async () => {
    const promise = service.listMine();
    const req = httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/holdings/mine`);
    expect(req.request.method).toBe('GET');
    req.flush({ total: 1, items: [holding()] });

    const result = await promise;
    expect(result.length).toBe(1);
    expect(service.myHoldings()[0].units).toBe(10);
  });

  it('fetchMine() GETs /holdings/mine/:id and sets current', async () => {
    const promise = service.fetchMine(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/holdings/mine/1`);
    expect(req.request.method).toBe('GET');
    req.flush(holding({ units: 25 }));

    const result = await promise;
    expect(result.units).toBe(25);
    expect(service.current()?.units).toBe(25);
  });
});
