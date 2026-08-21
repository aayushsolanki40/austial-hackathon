import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { environment } from '../../../environments/environment';
import { LedgerAccount } from '../../core/ledger/ledger.models';
import { MarketplaceListingDetail } from '../../core/marketplace/marketplace.models';
import { Subscription } from '../../core/subscriptions/subscriptions.models';
import AssetSubscribeComponent from './asset-subscribe.component';

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
    subscription_end_at: '2999-12-31T00:00:00Z',
    disclosures: [],
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
    proposal_id: 1,
    asset_name: 'Mumbai Commercial Tower',
    symbol: 'MCT',
    units_requested: 10,
    amount_usd: 1000,
    status: 'PENDING',
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

  function flushLoad(listingOverrides: Partial<MarketplaceListingDetail> = {}, accountOverrides: Partial<LedgerAccount> = {}): void {
    fixture.detectChanges();
    httpMock.expectOne(`${environment.apiBaseUrl}/issuance/marketplace/1`).flush(listingDetail(listingOverrides));
    httpMock.expectOne(`${environment.apiBaseUrl}/ledger/account`).flush(ledgerAccount(accountOverrides));
    flushMicrotasks();
  }

  it('loads the listing and the ledger account balance on init', fakeAsync(() => {
    flushLoad();
    expect(fixture.componentInstance.state()).toBe('loaded');
    expect(fixture.componentInstance.listing()?.asset_name).toBe('Mumbai Commercial Tower');
    expect(fixture.componentInstance.account()?.available_balance).toBe(5000);
  }));

  it('amountUsd() is units_requested * unit_price_usd', fakeAsync(() => {
    flushLoad();
    fixture.componentInstance.unitsForm.controls.units_requested.setValue(10);
    expect(fixture.componentInstance.amountUsd()).toBe(1000);
  }));

  it('hasSufficientFunds() is false when the amount exceeds available_balance', fakeAsync(() => {
    flushLoad({}, { available_balance: 500 });
    fixture.componentInstance.unitsForm.controls.units_requested.setValue(10);
    expect(fixture.componentInstance.hasSufficientFunds()).toBeFalse();
    expect(fixture.componentInstance.canSubmit()).toBeFalse();
  }));

  it('canSubmit() requires both risk and fee acknowledgment checkboxes', fakeAsync(() => {
    flushLoad();
    fixture.componentInstance.unitsForm.controls.units_requested.setValue(10);
    expect(fixture.componentInstance.canSubmit()).toBeFalse();

    fixture.componentInstance.riskAcknowledged.set(true);
    expect(fixture.componentInstance.canSubmit()).toBeFalse();

    fixture.componentInstance.feeAcknowledged.set(true);
    expect(fixture.componentInstance.canSubmit()).toBeTrue();
  }));

  it('submit() POSTs /subscriptions only once both checkboxes are acknowledged', fakeAsync(() => {
    flushLoad();
    const component = fixture.componentInstance;
    component.unitsForm.controls.units_requested.setValue(10);
    component.riskAcknowledged.set(true);
    component.feeAcknowledged.set(true);

    component.submit();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/subscriptions`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      proposal_id: 1,
      units_requested: 10,
      risk_acknowledged: true,
      fee_acknowledged: true,
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
    fixture.componentInstance.unitsForm.controls.units_requested.setValue(10);
    fixture.componentInstance.submit();
    httpMock.expectNone(`${environment.apiBaseUrl}/subscriptions`);
  }));
});
