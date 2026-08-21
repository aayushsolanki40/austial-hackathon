/** `LedgerAccountResponseDto` -- `GET /ledger/account`. One account per investor. This backend
 * is USD-only by construction at the transaction/ledger level, but the DTO still carries a plain
 * `currency` field (no `_usd` suffix on `available_balance`/`locked_balance` -- verified against
 * `src/modules/ledger/ledger_dto.py`). `locked_balance` will mostly read `0` until Phase 6 ships
 * fund-locking on subscribe. */
export interface LedgerAccount {
  id: number;
  currency: string;
  available_balance: number;
  locked_balance: number;
  created_at: string;
  updated_at: string;
}

/** `LedgerEntryResponseDto.entry_type` -- an open-ended string discriminator, not a closed enum
 * server-side. Confirmed values reachable from this build: `CREDIT_FUNDING` (a confirmed funding
 * instruction) and `DEBIT_PAYOUT` (a recorded payout). Credit-vs-debit display styling is derived
 * from the `CREDIT_`/`DEBIT_` prefix, not from a separate boolean/enum field -- see
 * `isCreditEntry()` in `ledger.service.ts`. */
export type LedgerEntryType = string;

/** `LedgerEntryResponseDto` -- one row of the append-only ledger. `balance_after` is the
 * reconstruction field the build plan calls out; `amount` is a plain number (sign/direction is
 * inferred from `entry_type`'s `CREDIT_`/`DEBIT_` prefix, not carried separately).
 * `reference_type`/`reference_id` together identify what caused the entry (e.g. a funding or
 * payout instruction row) -- there is no combined `reference` field. */
export interface LedgerEntry {
  id: number;
  entry_type: LedgerEntryType;
  amount: number;
  currency: string;
  balance_after: number;
  reference_type: string;
  reference_id: number | null;
  created_at: string;
}

/** Envelope for `GET /ledger/entries?skip=&take=`, mirroring the `{ total, items }` shape every
 * other paginated list endpoint in this backend uses. */
export interface LedgerEntryListResponse {
  total: number;
  items: LedgerEntry[];
}

/** `FundingInstruction` lifecycle status. `PENDING` until a compliance officer confirms the
 * matching wire via `POST /ledger/funding-instructions/:id/confirm`, then `CONFIRMED`. */
export type FundingInstructionStatus = 'PENDING' | 'CONFIRMED' | 'CANCELLED';

/** `RequestFundingInstructionDto` -- `POST /ledger/funding-instructions` request body. `amount`
 * is required (not an optional hint); `currency` is optional and defaults to `"USD"`
 * server-side. */
export interface RequestFundingInstructionRequest {
  amount: number;
  currency?: string;
}

/** `FundingInstructionResponseDto` -- returned by `POST /ledger/funding-instructions` and by
 * `GET /ledger/funding-instructions/mine/:id`. Wire/beneficiary details are flat top-level
 * fields, not a nested object. There is no investor-facing "list all my funding instructions"
 * endpoint -- only single-lookup-by-id (investor-scoped, ownership-checked server-side). */
export interface FundingInstruction {
  id: number;
  reference_code: string;
  amount: number;
  currency: string;
  status: FundingInstructionStatus;
  expires_at: string | null;
  confirmed_at: string | null;
  created_at: string;
  beneficiary_name: string;
  beneficiary_bank_name: string;
  beneficiary_account_number: string;
  beneficiary_swift_bic: string;
}
