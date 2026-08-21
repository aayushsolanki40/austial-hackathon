import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { environment } from '../../../environments/environment';
import { Holding } from '../../core/holdings/holdings.models';
import { Subscription } from '../../core/subscriptions/subscriptions.models';
import PortfolioComponent from './portfolio.component';

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

function subscription(overrides: Partial<Subscription> = {}): Subscription {
  return {
    id: 1,
    investor_id: 1,
    proposal_id: 1,
    asset_name: 'Goa Beachfront Resort',
    symbol: null,
    units_requested: 5,
    amount_usd: 500,
    status: 'PENDING',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('PortfolioComponent', () => {
  let fixture: ComponentFixture<PortfolioComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PortfolioComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(PortfolioComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function flushLoad(holdings: Holding[] = [], subscriptions: Subscription[] = []): void {
    fixture.detectChanges();
    httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/holdings/mine`).flush({ total: holdings.length, items: holdings });
    httpMock
      .expectOne((r) => r.url === `${environment.apiBaseUrl}/subscriptions/mine`)
      .flush({ total: subscriptions.length, items: subscriptions });
    flushMicrotasks();
  }

  it('loads holdings and subscriptions on init', fakeAsync(() => {
    flushLoad([holding()], [subscription()]);
    expect(fixture.componentInstance.state()).toBe('loaded');
    expect(fixture.componentInstance.holdings().length).toBe(1);
    expect(fixture.componentInstance.subscriptions().length).toBe(1);
  }));

  it('inFlightSubscriptions() only includes PENDING/FUNDED/CONFIRMED, excluding ALLOCATED/REFUNDED/CANCELLED', fakeAsync(() => {
    flushLoad(
      [],
      [
        subscription({ id: 1, status: 'PENDING' }),
        subscription({ id: 2, status: 'FUNDED' }),
        subscription({ id: 3, status: 'CONFIRMED' }),
        subscription({ id: 4, status: 'ALLOCATED' }),
        subscription({ id: 5, status: 'REFUNDED' }),
        subscription({ id: 6, status: 'CANCELLED' }),
      ],
    );

    const inFlightIds = fixture.componentInstance.inFlightSubscriptions().map((s) => s.id);
    expect(inFlightIds).toEqual([1, 2, 3]);
  }));

  it('falls back to the error state when either request fails', fakeAsync(() => {
    fixture.detectChanges();
    httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/holdings/mine`).flush('error', { status: 500, statusText: 'Server Error' });
    httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/subscriptions/mine`).flush({ total: 0, items: [] });
    flushMicrotasks();

    expect(fixture.componentInstance.state()).toBe('error');
  }));
});
