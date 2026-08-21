import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { FundingInstruction, LedgerAccount, LedgerEntry } from './ledger.models';
import { LEDGER_ENTRY_PAGE_SIZE, LedgerService } from './ledger.service';

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

  it('starts with no account, no entries, and no funding instructions', () => {
    expect(service.account()).toBeNull();
    expect(service.entries()).toEqual([]);
    expect(service.entriesTotal()).toBe(0);
    expect(service.fundingInstructions()).toEqual([]);
  });

  it('fetchAccount() GETs /ledger/account and stores the result', async () => {
    const promise = service.fetchAccount();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/ledger/account`);
    expect(req.request.method).toBe('GET');
    req.flush(ledgerAccount());

    const result = await promise;
    expect(result.available_balance_usd).toBe(5000);
    expect(service.account()?.locked_balance_usd).toBe(0);
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
    expect(service.entries()[0].balance_after_usd).toBe(5000);
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

  it('listFundingInstructions() GETs /ledger/funding-instructions and stores items', async () => {
    const promise = service.listFundingInstructions();
    const req = httpMock.expectOne((r) => r.url === `${environment.apiBaseUrl}/ledger/funding-instructions`);
    expect(req.request.method).toBe('GET');
    req.flush({ total: 1, items: [fundingInstruction()] });

    const result = await promise;
    expect(result.length).toBe(1);
    expect(service.fundingInstructions()[0].reference_code).toBe('SWD-REF-0001');
  });

  it('requestFundingInstructions() POSTs /ledger/funding-instructions and prepends the response', async () => {
    const promise = service.requestFundingInstructions({ expected_amount_usd: 5000 });
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/ledger/funding-instructions`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ expected_amount_usd: 5000 });
    req.flush(fundingInstruction());

    const result = await promise;
    expect(result.reference_code).toBe('SWD-REF-0001');
    expect(service.fundingInstructions()[0].id).toBe(1);
  });

  it('requestFundingInstructions() defaults to an empty body when no amount is provided', async () => {
    const promise = service.requestFundingInstructions();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/ledger/funding-instructions`);
    expect(req.request.body).toEqual({});
    req.flush(fundingInstruction());

    await promise;
  });
});
