import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { MarketplaceListing, MarketplaceListingDetail } from './marketplace.models';
import { MarketplaceService } from './marketplace.service';

function listing(overrides: Partial<MarketplaceListing> = {}): MarketplaceListing {
  return {
    id: 1,
    asset_id: 1,
    asset_name: 'Mumbai Commercial Tower',
    asset_class: 'REAL_ESTATE',
    asset_description: 'A commercial office tower.',
    issuer_id: 1,
    token_series_id: 1,
    symbol: 'MCT',
    total_units: 10000,
    units_subscribed: 0,
    unit_price_usd: 100,
    min_subscription_units: 10,
    subscription_start_at: '2026-01-01T00:00:00Z',
    subscription_end_at: '2026-12-31T00:00:00Z',
    ...overrides,
  };
}

function listingDetail(overrides: Partial<MarketplaceListingDetail> = {}): MarketplaceListingDetail {
  return { ...listing(), disclosures: [], ...overrides };
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

  it('starts with no listings and no current listing', () => {
    expect(service.listings()).toEqual([]);
    expect(service.current()).toBeNull();
  });

  it('listListings() GETs /issuance/marketplace and stores items', async () => {
    const promise = service.listListings();
    const req = httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/issuance/marketplace`);
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('asset_class')).toBeNull();
    req.flush({ total: 1, items: [listing()] });

    const result = await promise;
    expect(result.length).toBe(1);
    expect(service.listings()[0].asset_name).toBe('Mumbai Commercial Tower');
  });

  it('listListings(assetClass) sends the asset_class filter as a query param', async () => {
    const promise = service.listListings('REAL_ESTATE');
    const req = httpMock.expectOne(
      (r) => r.url === `${environment.apiBaseUrl}/issuance/marketplace` && r.params.get('asset_class') === 'REAL_ESTATE',
    );
    req.flush({ total: 0, items: [] });
    await promise;
  });

  it('fetchListing() GETs /issuance/marketplace/:id and sets current', async () => {
    const promise = service.fetchListing(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/marketplace/1`);
    expect(req.request.method).toBe('GET');
    req.flush(listingDetail());

    const result = await promise;
    expect(result.id).toBe(1);
    expect(service.current()?.id).toBe(1);
  });
});
