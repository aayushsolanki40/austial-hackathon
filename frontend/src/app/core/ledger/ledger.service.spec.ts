import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { FundingInstruction, LedgerAccount, LedgerEntry } from './ledger.models';
import { isCreditEntry, LEDGER_ENTRY_PAGE_SIZE, LedgerService } from './ledger.service';

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
    beneficiary_name: 'Austial Client Funds Account',
    beneficiary_bank_name: 'GIFT City IBU Bank',
    beneficiary_account_number: '000123456789',
    beneficiary_swift_bic: 'GIFTINBBXXX',
    ...overrides,
  };
}

describe('LedgerService', () => {
  let service: LedgerService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(LedgerService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('starts with no account, no entries, and no funding instruction', () => {
    expect(service.account()).toBeNull();
    expect(service.entries()).toEqual([]);
    expect(service.entriesTotal()).toBe(0);
    expect(service.fundingInstruction()).toBeNull();
  });

  it('fetchAccount() GETs /ledger/account and stores the result', async () => {
    const promise = service.fetchAccount();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/ledger/account`);
    expect(req.request.method).toBe('GET');
    req.flush(ledgerAccount());

    const result = await promise;
    expect(result.available_balance).toBe(5000);
    expect(service.account()?.locked_balance).toBe(0);
  });

  it('fetchEntries() GETs /ledger/entries with skip/take defaults and stores items + pagination', async () => {
    const promise = service.fetchEntries();
    const req = httpMock.expectOne(
      (r) => r.url === `${environment.apiBaseUrl}/ledger/entries` && r.params.get('skip') === '0' && r.params.get('take') === String(LEDGER_ENTRY_PAGE_SIZE),
    );
    expect(req.request.method).toBe('GET');
    req.flush({ total: 1, items: [ledgerEntry()] });

    const result = await promise;
    expect(result.length).toBe(1);
    expect(service.entries()[0].balance_after).toBe(5000);
    expect(service.entriesTotal()).toBe(1);
    expect(service.entriesSkip()).toBe(0);
  });

  it('nextEntriesPage() advances skip by the page size', async () => {
    const firstPromise = service.fetchEntries();
    httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/ledger/entries`).flush({ total: 40, items: [ledgerEntry()] });
    await firstPromise;

    const nextPromise = service.nextEntriesPage();
    const req = httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/ledger/entries` && r.params.get('skip') === String(LEDGER_ENTRY_PAGE_SIZE));
    req.flush({ total: 40, items: [ledgerEntry({ id: 2 })] });

    await nextPromise;
    expect(service.entriesSkip()).toBe(LEDGER_ENTRY_PAGE_SIZE);
    expect(service.entries()[0].id).toBe(2);
  });

  it('previousEntriesPage() never goes below skip=0', async () => {
    const promise = service.previousEntriesPage();
    const req = httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/ledger/entries` && r.params.get('skip') === '0');
    req.flush({ total: 0, items: [] });

    await promise;
    expect(service.entriesSkip()).toBe(0);
  });

  it('requestFundingInstruction() POSTs /ledger/funding-instructions with amount and stores the response', async () => {
    const promise = service.requestFundingInstruction({ amount: 5000 });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/ledger/funding-instructions`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ amount: 5000 });
    req.flush(fundingInstruction());

    const result = await promise;
    expect(result.reference_code).toBe('SWD-REF-0001');
    expect(service.fundingInstruction()?.id).toBe(1);
  });

  it('fetchFundingInstruction() GETs /ledger/funding-instructions/mine/:id and stores the response', async () => {
    const promise = service.fetchFundingInstruction(1);
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/ledger/funding-instructions/mine/1`);
    expect(req.request.method).toBe('GET');
    req.flush(fundingInstruction({ status: 'CONFIRMED' }));

    const result = await promise;
    expect(result.status).toBe('CONFIRMED');
    expect(service.fundingInstruction()?.status).toBe('CONFIRMED');
  });

  it('isCreditEntry() derives credit/debit from the entry_type prefix', () => {
    expect(isCreditEntry('CREDIT_FUNDING')).toBeTrue();
    expect(isCreditEntry('DEBIT_PAYOUT')).toBeFalse();
  });
});
