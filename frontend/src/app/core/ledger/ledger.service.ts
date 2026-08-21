import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { ApiService } from '../api/api.service';
import { FundingInstruction, LedgerAccount, LedgerEntry, LedgerEntryListResponse, RequestFundingInstructionRequest } from './ledger.models';

export const LEDGER_ENTRY_PAGE_SIZE = 20;

/** Route prefix confirmed against the backend's `src/i18n/locales/en/ledger.json`
 * (`route_prefix: "ledger"`), not guessed. */
const LEDGER_ROUTE_PREFIX = '/ledger';

/** Derives credit/debit display styling from `entry_type`'s `CREDIT_`/`DEBIT_` prefix -- the
 * backend does not carry a separate `direction` field. */
export function isCreditEntry(entryType: string): boolean {
  return entryType.startsWith('CREDIT_');
}

@Injectable({ providedIn: 'root' })
export class LedgerService {
  private readonly api = inject(ApiService);

  private readonly accountSignal = signal<LedgerAccount | null>(null);
  private readonly entriesSignal = signal<LedgerEntry[]>([]);
  private readonly entriesTotalSignal = signal(0);
  private readonly entriesSkipSignal = signal(0);
  private readonly fundingInstructionSignal = signal<FundingInstruction | null>(null);

  readonly account = this.accountSignal.asReadonly();
  readonly entries = this.entriesSignal.asReadonly();
  readonly entriesTotal = this.entriesTotalSignal.asReadonly();
  readonly entriesSkip = this.entriesSkipSignal.asReadonly();
  /** The most recently requested (or re-checked) funding instruction. There is no
   * investor-facing "list all my funding instructions" endpoint -- only single-lookup, so this
   * holds at most one instruction at a time rather than a list. */
  readonly fundingInstruction = this.fundingInstructionSignal.asReadonly();

  /** `GET /ledger/account` -- the caller's own account, scoped server-side. Sets `account`. */
  async fetchAccount(): Promise<LedgerAccount> {
    const account = await firstValueFrom(this.api.get<LedgerAccount>(`${LEDGER_ROUTE_PREFIX}/account`));
    this.accountSignal.set(account);
    return account;
  }

  /** `GET /ledger/entries?skip=&take=` -- paginated ledger history, which is the actual
   * "transaction history" view (a `CREDIT_FUNDING` entry appears here once compliance confirms a
   * funding instruction). Unwraps `{ total, items }` and records `skip` so `nextEntriesPage()`/
   * `previousEntriesPage()` can page without the caller tracking offset state itself. */
  async fetchEntries(skip = 0, take = LEDGER_ENTRY_PAGE_SIZE): Promise<LedgerEntry[]> {
    const response = await firstValueFrom(
      this.api.get<LedgerEntryListResponse>(`${LEDGER_ROUTE_PREFIX}/entries`, { skip, take }),
    );
    this.entriesSignal.set(response.items);
    this.entriesTotalSignal.set(response.total);
    this.entriesSkipSignal.set(skip);
    return response.items;
  }

  async nextEntriesPage(): Promise<LedgerEntry[]> {
    return this.fetchEntries(this.entriesSkipSignal() + LEDGER_ENTRY_PAGE_SIZE);
  }

  async previousEntriesPage(): Promise<LedgerEntry[]> {
    return this.fetchEntries(Math.max(0, this.entriesSkipSignal() - LEDGER_ENTRY_PAGE_SIZE));
  }

  /** `POST /ledger/funding-instructions` -- requested on-demand by the investor entering an
   * amount and clicking "Request funding instructions"; the backend allocates a fresh
   * `reference_code` and returns the wire details to include in the bank transfer. */
  async requestFundingInstruction(request: RequestFundingInstructionRequest): Promise<FundingInstruction> {
    const instruction = await firstValueFrom(
      this.api.post<FundingInstruction>(`${LEDGER_ROUTE_PREFIX}/funding-instructions`, request),
    );
    this.fundingInstructionSignal.set(instruction);
    return instruction;
  }

  /** `GET /ledger/funding-instructions/mine/:id` -- investor-scoped, ownership-checked
   * single-instruction lookup, used to re-check a specific instruction's status (e.g. whether it
   * has moved from `PENDING` to `CONFIRMED`). There is no list-all-mine endpoint. */
  async fetchFundingInstruction(id: number): Promise<FundingInstruction> {
    const instruction = await firstValueFrom(
      this.api.get<FundingInstruction>(`${LEDGER_ROUTE_PREFIX}/funding-instructions/mine/${id}`),
    );
    this.fundingInstructionSignal.set(instruction);
    return instruction;
  }
}
