import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { environment } from '../../../environments/environment';
import { MarketplaceTokenSeries } from '../../core/marketplace/marketplace.models';
import MarketplaceComponent from './marketplace.component';

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
    return httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/subscriptions/marketplace`);
  }

  it('loads listings from GET /subscriptions/marketplace on init', fakeAsync(() => {
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

  it('setAssetClassFilter() filters the already-loaded listings client-side, without a refetch', fakeAsync(() => {
    fixture.detectChanges();
    expectListingsReq().flush({
      total: 2,
      items: [listing({ id: 1, asset_class: 'REAL_ESTATE' }), listing({ id: 2, asset_class: 'COMMODITY' })],
    });
    flushMicrotasks();

    fixture.componentInstance.setAssetClassFilter('COMMODITY');
    httpMock.expectNone((r) => r.url === `${environment.apiBaseUrl}/subscriptions/marketplace`);

    expect(fixture.componentInstance.selectedAssetClass()).toBe('COMMODITY');
    expect(fixture.componentInstance.listings().length).toBe(1);
    expect(fixture.componentInstance.listings()[0].id).toBe(2);
  }));
});
