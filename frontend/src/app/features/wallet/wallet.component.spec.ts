import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { FundingInstruction, LedgerAccount, LedgerEntry } from '../../core/ledger/ledger.models';
import WalletComponent from './wallet.component';

function ledgerAccount(overrides: Partial<LedgerAccount> = {}): LedgerAccount {
  return {
    id: 1,
    investor_id: 1,
    available_balance_usd: 5000,
    locked_balance_usd: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function ledgerEntry(overrides: Partial<LedgerEntry> = {}): LedgerEntry {
  return {
    id: 1,
    account_id: 1,
    entry_type: 'FUNDING_CREDIT',
    direction: 'CREDIT',
    amount_usd: 5000,
    balance_after_usd: 5000,
    reference: 'SWD-REF-0001',
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function fundingInstruction(overrides: Partial<FundingInstruction> = {}): FundingInstruction {
  return {
    id: 1,
    account_id: 1,
    reference_code: 'SWD-REF-0001',
    status: 'PENDING',
    expected_amount_usd: 5000,
    beneficiary_bank_name: 'GIFT City IBU Bank',
    beneficiary_account_name: 'Swadely Client Funds Account',
    beneficiary_account_number: '000123456789',
    beneficiary_swift_bic: 'GIFTINBBXXX',
    beneficiary_bank_address: 'GIFT City, Gandhinagar, Gujarat, India',
    intermediary_bank_swift_bic: null,
    created_at: '2026-01-01T00:00:00Z',
    confirmed_at: null,
    ...overrides,
  };
}

describe('WalletComponent', () => {
  let fixture: ComponentFixture<WalletComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WalletComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(WalletComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function expectAccountReq() {
    return httpMock.expectOne(`${environment.apiBaseUrl}/ledger/account`);
  }

  function expectFundingReq() {
    return httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/ledger/funding-instructions`);
  }

  function expectEntriesReq() {
    return httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/ledger/entries`);
  }

  it('loads and displays the account balance from GET /ledger/account', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount({ available_balance_usd: 1234.5, locked_balance_usd: 0 }));
    expectFundingReq().flush({ total: 0, items: [] });
    expectEntriesReq().flush({ total: 0, items: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.accountState()).toBe('loaded');
    expect(fixture.componentInstance.account()?.available_balance_usd).toBe(1234.5);
  });

  it('falls back to the error state when /ledger/account is unavailable', async () => {
    fixture.detectChanges();
    expectAccountReq().flush('not found', { status: 404, statusText: 'Not Found' });
    expectFundingReq().flush({ total: 0, items: [] });
    expectEntriesReq().flush({ total: 0, items: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.accountState()).toBe('error');
  });

  it('lists funding instructions from GET /ledger/funding-instructions', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount());
    expectFundingReq().flush({ total: 1, items: [fundingInstruction()] });
    expectEntriesReq().flush({ total: 0, items: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.fundingState()).toBe('loaded');
    expect(fixture.componentInstance.fundingInstructions()[0].reference_code).toBe('SWD-REF-0001');
  });

  it('requestFundingInstructions() POSTs /ledger/funding-instructions with the entered amount and prepends the result', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount());
    expectFundingReq().flush({ total: 0, items: [] });
    expectEntriesReq().flush({ total: 0, items: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    const component = fixture.componentInstance;
    component.setExpectedAmount('2500');
    const promise = component.requestFundingInstructions();

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/ledger/funding-instructions`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ expected_amount_usd: 2500 });
    req.flush(fundingInstruction({ expected_amount_usd: 2500 }));
    await promise;

    expect(component.fundingInstructions()[0].expected_amount_usd).toBe(2500);
    expect(component.expectedAmountInput()).toBe('');
  });

  it('requestFundingInstructions() sends an empty body when no amount is entered', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount());
    expectFundingReq().flush({ total: 0, items: [] });
    expectEntriesReq().flush({ total: 0, items: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    const promise = fixture.componentInstance.requestFundingInstructions();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/ledger/funding-instructions`);
    expect(req.request.body).toEqual({});
    req.flush(fundingInstruction());
    await promise;
  });

  it('surfaces a request error and does not clear the entered amount on failure', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount());
    expectFundingReq().flush({ total: 0, items: [] });
    expectEntriesReq().flush({ total: 0, items: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    const component = fixture.componentInstance;
    component.setExpectedAmount('100');
    const promise = component.requestFundingInstructions();
    httpMock.expectOne(`${environment.apiBaseUrl}/ledger/funding-instructions`).flush('error', { status: 500, statusText: 'Server Error' });
    await promise;

    expect(component.requestError()).toBeTruthy();
    expect(component.expectedAmountInput()).toBe('100');
  });

  it('loads paginated ledger entries from GET /ledger/entries with skip=0/take=pageSize', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount());
    expectFundingReq().flush({ total: 0, items: [] });
    const req = expectEntriesReq();
    expect(req.request.params.get('skip')).toBe('0');
    expect(req.request.params.get('take')).toBe(String(fixture.componentInstance.pageSize));
    req.flush({ total: 1, items: [ledgerEntry()] });
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.entriesState()).toBe('loaded');
    expect(fixture.componentInstance.entries()[0].balance_after_usd).toBe(5000);
    expect(fixture.componentInstance.hasNextPage).toBeFalse();
    expect(fixture.componentInstance.hasPreviousPage).toBeFalse();
  });

  it('nextPage() advances to the next page of ledger entries', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount());
    expectFundingReq().flush({ total: 0, items: [] });
    expectEntriesReq().flush({ total: 40, items: [ledgerEntry()] });
    await fixture.whenStable();
    fixture.detectChanges();

    const component = fixture.componentInstance;
    expect(component.hasNextPage).toBeTrue();

    const promise = component.nextPage();
    const req = httpMock.expectOne(
      (r) => r.url === `${environment.apiBaseUrl}/ledger/entries` && r.params.get('skip') === String(component.pageSize),
    );
    req.flush({ total: 40, items: [ledgerEntry({ id: 2 })] });
    await promise;

    expect(component.entries()[0].id).toBe(2);
    expect(component.hasPreviousPage).toBeTrue();
  });

  it('falls back to the error state when /ledger/entries is unavailable', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount());
    expectFundingReq().flush({ total: 0, items: [] });
    expectEntriesReq().flush('forbidden', { status: 403, statusText: 'Forbidden' });
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.entriesState()).toBe('error');
  });
});
