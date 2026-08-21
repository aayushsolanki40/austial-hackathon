import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { FundingInstruction, LedgerAccount, LedgerEntry } from '../../core/ledger/ledger.models';
import WalletComponent from './wallet.component';

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

function ledgerEntry(overrides: Partial<LedgerEntry> = {}): LedgerEntry {
  return {
    id: 1,
    entry_type: 'CREDIT_FUNDING',
    amount: 5000,
    currency: 'USD',
    balance_after: 5000,
    reference_type: 'funding_instruction',
    reference_id: 1,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function fundingInstruction(overrides: Partial<FundingInstruction> = {}): FundingInstruction {
  return {
    id: 1,
    reference_code: 'SWD-REF-0001',
    amount: 5000,
    currency: 'USD',
    status: 'PENDING',
    expires_at: null,
    confirmed_at: null,
    created_at: '2026-01-01T00:00:00Z',
    beneficiary_name: 'Swadely Client Funds Account',
    beneficiary_bank_name: 'GIFT City IBU Bank',
    beneficiary_account_number: '000123456789',
    beneficiary_swift_bic: 'GIFTINBBXXX',
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

  function expectEntriesReq() {
    return httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/ledger/entries`);
  }

  it('loads and displays the account balance from GET /ledger/account', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount({ available_balance: 1234.5, locked_balance: 0 }));
    expectEntriesReq().flush({ total: 0, items: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.accountState()).toBe('loaded');
    expect(fixture.componentInstance.account()?.available_balance).toBe(1234.5);
  });

  it('falls back to the error state when /ledger/account is unavailable', async () => {
    fixture.detectChanges();
    expectAccountReq().flush('not found', { status: 404, statusText: 'Not Found' });
    expectEntriesReq().flush({ total: 0, items: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.accountState()).toBe('error');
  });

  it('requestFundingInstruction() POSTs /ledger/funding-instructions with the entered amount', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount());
    expectEntriesReq().flush({ total: 0, items: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    const component = fixture.componentInstance;
    component.setAmount('2500');
    const promise = component.requestFundingInstruction();

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/ledger/funding-instructions`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ amount: 2500 });
    req.flush(fundingInstruction({ amount: 2500 }));
    await promise;

    expect(component.fundingInstruction()?.amount).toBe(2500);
    expect(component.fundingInstruction()?.reference_code).toBe('SWD-REF-0001');
    expect(component.amountInput()).toBe('');
  });

  it('requestFundingInstruction() surfaces a validation error and does not call the API when no amount is entered', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount());
    expectEntriesReq().flush({ total: 0, items: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    await fixture.componentInstance.requestFundingInstruction();

    expect(fixture.componentInstance.requestError()).toBeTruthy();
    httpMock.expectNone(`${environment.apiBaseUrl}/ledger/funding-instructions`);
  });

  it('surfaces a request error and does not clear the entered amount on failure', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount());
    expectEntriesReq().flush({ total: 0, items: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    const component = fixture.componentInstance;
    component.setAmount('100');
    const promise = component.requestFundingInstruction();
    httpMock.expectOne(`${environment.apiBaseUrl}/ledger/funding-instructions`).flush('error', { status: 500, statusText: 'Server Error' });
    await promise;

    expect(component.requestError()).toBeTruthy();
    expect(component.amountInput()).toBe('100');
  });

  it('checkFundingStatus() re-fetches the instruction via GET /ledger/funding-instructions/mine/:id', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount());
    expectEntriesReq().flush({ total: 0, items: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    const component = fixture.componentInstance;
    component.setAmount('2500');
    const requestPromise = component.requestFundingInstruction();
    httpMock.expectOne(`${environment.apiBaseUrl}/ledger/funding-instructions`).flush(fundingInstruction());
    await requestPromise;

    const checkPromise = component.checkFundingStatus();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/ledger/funding-instructions/mine/1`);
    expect(req.request.method).toBe('GET');
    req.flush(fundingInstruction({ status: 'CONFIRMED' }));
    await checkPromise;

    expect(component.fundingInstruction()?.status).toBe('CONFIRMED');
  });

  it('loads paginated ledger entries from GET /ledger/entries with skip=0/take=pageSize', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount());
    const req = expectEntriesReq();
    expect(req.request.params.get('skip')).toBe('0');
    expect(req.request.params.get('take')).toBe(String(fixture.componentInstance.pageSize));
    req.flush({ total: 1, items: [ledgerEntry()] });
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.entriesState()).toBe('loaded');
    expect(fixture.componentInstance.entries()[0].balance_after).toBe(5000);
    expect(fixture.componentInstance.hasNextPage).toBeFalse();
    expect(fixture.componentInstance.hasPreviousPage).toBeFalse();
  });

  it('nextPage() advances to the next page of ledger entries', async () => {
    fixture.detectChanges();
    expectAccountReq().flush(ledgerAccount());
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
    expectEntriesReq().flush('forbidden', { status: 403, statusText: 'Forbidden' });
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.componentInstance.entriesState()).toBe('error');
  });

  it('derives credit/debit styling from the entry_type prefix, not a separate field', () => {
    expect(fixture.componentInstance.isCreditEntry('CREDIT_FUNDING')).toBeTrue();
    expect(fixture.componentInstance.isCreditEntry('DEBIT_PAYOUT')).toBeFalse();
  });
});
