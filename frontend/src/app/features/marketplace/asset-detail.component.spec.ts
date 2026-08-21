import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { environment } from '../../../environments/environment';
import { MarketplaceListingDetail } from '../../core/marketplace/marketplace.models';
import AssetDetailComponent from './asset-detail.component';

function listingDetail(overrides: Partial<MarketplaceListingDetail> = {}): MarketplaceListingDetail {
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
    subscription_start_at: '2020-01-01T00:00:00Z',
    subscription_end_at: '2020-12-31T00:00:00Z',
    disclosures: [],
    ...overrides,
  };
}

describe('AssetDetailComponent', () => {
  let fixture: ComponentFixture<AssetDetailComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AssetDetailComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: '1' }) } },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AssetDetailComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('loads the listing by id from the route via /issuance/marketplace/:id', fakeAsync(() => {
    fixture.detectChanges();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/marketplace/1`);
    expect(req.request.method).toBe('GET');
    req.flush(listingDetail());
    flushMicrotasks();

    expect(fixture.componentInstance.state()).toBe('loaded');
    expect(fixture.componentInstance.listing()?.asset_name).toBe('Mumbai Commercial Tower');
  }));

  it('windowOpen() is false once the subscription window has closed', fakeAsync(() => {
    fixture.detectChanges();
    httpMock
      .expectOne(`${environment.apiBaseUrl}/issuance/marketplace/1`)
      .flush(listingDetail({ subscription_start_at: '2020-01-01T00:00:00Z', subscription_end_at: '2020-12-31T00:00:00Z' }));
    flushMicrotasks();

    expect(fixture.componentInstance.windowOpen()).toBeFalse();
  }));

  it('windowOpen() is true while now falls within the subscription window', fakeAsync(() => {
    fixture.detectChanges();
    httpMock
      .expectOne(`${environment.apiBaseUrl}/issuance/marketplace/1`)
      .flush(listingDetail({ subscription_start_at: '2020-01-01T00:00:00Z', subscription_end_at: '2999-12-31T00:00:00Z' }));
    flushMicrotasks();

    expect(fixture.componentInstance.windowOpen()).toBeTrue();
  }));
});
