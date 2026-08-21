import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { environment } from '../../../environments/environment';
import { LedgerAccount } from '../../core/ledger/ledger.models';
import { MarketplaceTokenSeries } from '../../core/marketplace/marketplace.models';
import { Subscription } from '../../core/subscriptions/subscriptions.models';
import AssetSubscribeComponent from './asset-subscribe.component';

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
    subscription_start_at: '2020-01-01T00:00:00Z',
    subscription_end_at: '2999-12-31T00:00:00Z',
    ...overrides,
  };
}

function ledgerAccount(overrides: Partial<LedgerAccount> = {}): LedgerAccount {
  return {
    id: 1,
    currency: 'USD',
    available_balance: 5000,
    locked_balance: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

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

describe('AssetSubscribeComponent', () => {
  let fixture: ComponentFixture<AssetSubscribeComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AssetSubscribeComponent],
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

    fixture = TestBed.createComponent(AssetSubscribeComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function flushLoad(listingOverrides: Partial<MarketplaceTokenSeries> = {}, accountOverrides: Partial<LedgerAccount> = {}): void {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/subscriptions/marketplace`).flush({ total: 1, items: [listing(listingOverrides)] });
    httpMock.expectOne(`${environment.apiBaseUrl}/ledger/account`).flush(ledgerAccount(accountOverrides));
    flushMicrotasks();
  }

  it('loads the listing and the ledger account balance on init', fakeAsync(() => {
    flushLoad();
    expect(fixture.componentInstance.state()).toBe('loaded');
    expect(fixture.componentInstance.listing()?.asset_name).toBe('Mumbai Commercial Tower');
    expect(fixture.componentInstance.account()?.available_balance).toBe(5000);
  }));

  it('amountUsd() is units * unit_price_usd', fakeAsync(() => {
    flushLoad();
    fixture.componentInstance.unitsForm.controls.units.setValue(10);
    expect(fixture.componentInstance.amountUsd()).toBe(1000);
  }));

  it('hasSufficientFunds() is false when the amount exceeds available_balance', fakeAsync(() => {
    flushLoad({}, { available_balance: 500 });
    fixture.componentInstance.unitsForm.controls.units.setValue(10);
    expect(fixture.componentInstance.hasSufficientFunds()).toBeFalse();
    expect(fixture.componentInstance.canSubmit()).toBeFalse();
  }));

  it('canSubmit() requires both risk and fee acknowledgment checkboxes', fakeAsync(() => {
    flushLoad();
    fixture.componentInstance.unitsForm.controls.units.setValue(10);
    expect(fixture.componentInstance.canSubmit()).toBeFalse();

    fixture.componentInstance.riskAcknowledged.set(true);
    expect(fixture.componentInstance.canSubmit()).toBeFalse();

    fixture.componentInstance.feeAcknowledged.set(true);
    expect(fixture.componentInstance.canSubmit()).toBeTrue();
  }));

  it('submit() POSTs /subscriptions only once both checkboxes are acknowledged', fakeAsync(() => {
    flushLoad();
    const component = fixture.componentInstance;
    component.unitsForm.controls.units.setValue(10);
    component.riskAcknowledged.set(true);
    component.feeAcknowledged.set(true);

    component.submit();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/subscriptions`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      token_series_id: 1,
      units: 10,
      risk_disclosure_accepted: true,
      fee_disclosure_accepted: true,
    });
    req.flush(subscription());
    flushMicrotasks();
    httpMock.expectOne(`${environment.apiBaseUrl}/ledger/account`).flush(ledgerAccount({ available_balance: 4000, locked_balance: 1000 }));
    flushMicrotasks();

    expect(component.result()?.status).toBe('PENDING');
    expect(component.account()?.locked_balance).toBe(1000);
  }));

  it('submit() does nothing when the acknowledgment checkboxes are unchecked', fakeAsync(() => {
    flushLoad();
    fixture.componentInstance.unitsForm.controls.units.setValue(10);
    fixture.componentInstance.submit();
    flushMicrotasks();

    expect(fixture.componentInstance.result()).toBeNull();
    httpMock.expectNone(`${environment.apiBaseUrl}/subscriptions`);
  }));
});
