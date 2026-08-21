import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { environment } from '../../../environments/environment';
import { MarketplaceListing } from '../../core/marketplace/marketplace.models';
import MarketplaceComponent from './marketplace.component';

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

describe('MarketplaceComponent', () => {
  let fixture: ComponentFixture<MarketplaceComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MarketplaceComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(MarketplaceComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function expectListingsReq() {
    return httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/issuance/marketplace`);
  }

  it('loads listings from GET /issuance/marketplace on init', fakeAsync(() => {
    fixture.detectChanges();
    expectListingsReq().flush({ total: 1, items: [listing()] });
    flushMicrotasks();

    expect(fixture.componentInstance.state()).toBe('loaded');
    expect(fixture.componentInstance.listings().length).toBe(1);
  }));

  it('falls back to the error state when the marketplace listing fails', fakeAsync(() => {
    fixture.detectChanges();
    expectListingsReq().flush('error', { status: 500, statusText: 'Server Error' });
    flushMicrotasks();

    expect(fixture.componentInstance.state()).toBe('error');
  }));

  it('setAssetClassFilter() reloads with the asset_class query param', fakeAsync(() => {
    fixture.detectChanges();
    expectListingsReq().flush({ total: 1, items: [listing()] });
    flushMicrotasks();

    fixture.componentInstance.setAssetClassFilter('COMMODITY');
    const req = httpMock.expectOne(
      (r) => r.url === `${environment.apiBaseUrl}/issuance/marketplace` && r.params.get('asset_class') === 'COMMODITY',
    );
    req.flush({ total: 0, items: [] });
    flushMicrotasks();

    expect(fixture.componentInstance.selectedAssetClass()).toBe('COMMODITY');
    expect(fixture.componentInstance.listings().length).toBe(0);
  }));
});
