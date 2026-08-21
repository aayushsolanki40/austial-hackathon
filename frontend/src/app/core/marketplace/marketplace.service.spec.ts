import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { MarketplaceTokenSeries } from './marketplace.models';
import { MarketplaceService } from './marketplace.service';

function listing(overrides: Partial<MarketplaceTokenSeries> = {}): MarketplaceTokenSeries {
  return {
    id: 1,
    symbol: 'MCT',
    asset_id: 1,
    asset_name: 'Mumbai Commercial Tower',
    asset_class: 'REAL_ESTATE',
    issuer_id: 1,
    total_supply: 10000,
    unit_price_usd: 100,
    min_subscription_units: 10,
    subscription_start_at: '2026-01-01T00:00:00Z',
    subscription_end_at: '2026-12-31T00:00:00Z',
    ...overrides,
  };
}

describe('MarketplaceService', () => {
  let service: MarketplaceService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(MarketplaceService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('starts with no listings', () => {
    expect(service.listings()).toEqual([]);
  });

  it('listListings() GETs /subscriptions/marketplace and stores items', async () => {
    const promise = service.listListings();
    const req = httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/subscriptions/marketplace`);
    expect(req.request.method).toBe('GET');
    req.flush({ total: 1, items: [listing()] });

    const result = await promise;
    expect(result.length).toBe(1);
    expect(service.listings()[0].asset_name).toBe('Mumbai Commercial Tower');
  });

  it('findById() looks a series up in the already-loaded listings', async () => {
    const promise = service.listListings();
    httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/subscriptions/marketplace`).flush({ total: 1, items: [listing()] });
    await promise;

    expect(service.findById(1)?.asset_name).toBe('Mumbai Commercial Tower');
    expect(service.findById(2)).toBeUndefined();
  });
});
