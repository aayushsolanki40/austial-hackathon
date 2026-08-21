import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';

import { I18nService } from '../../core/i18n/i18n.service';
import { TPipe } from '../../core/i18n/t.pipe';
import { isCreditEntry, LEDGER_ENTRY_PAGE_SIZE, LedgerService } from '../../core/ledger/ledger.service';

type LoadState = 'loading' | 'error' | 'loaded';

@Component({
  selector: 'app-wallet',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, MatButtonModule, MatFormFieldModule, MatInputModule, MatProgressSpinnerModule, MatTableModule, TPipe],
  templateUrl: './wallet.component.html',
  styleUrl: './wallet.component.scss',
})
export default class WalletComponent implements OnInit {
  private readonly ledger = inject(LedgerService);
  private readonly i18n = inject(I18nService);

  readonly pageSize = LEDGER_ENTRY_PAGE_SIZE;
  readonly isCreditEntry = isCreditEntry;

  readonly account = this.ledger.account;
  readonly accountState = signal<LoadState>('loading');

  readonly fundingInstruction = this.ledger.fundingInstruction;
  readonly requestingFunding = signal(false);
  readonly requestError = signal<string | null>(null);
  readonly checkingStatus = signal(false);
  readonly amountInput = signal('');

  readonly entries = this.ledger.entries;
  readonly entriesTotal = this.ledger.entriesTotal;
  readonly entriesSkip = this.ledger.entriesSkip;
  readonly entriesState = signal<LoadState>('loading');
  readonly entryColumns = ['created_at', 'entry_type', 'amount', 'balance_after', 'reference'];

  ngOnInit(): void {
    this.loadAccount();
    this.loadEntries();
  }

  loadAccount(): void {
    this.accountState.set('loading');
    this.ledger
      .fetchAccount()
      .then(() => this.accountState.set('loaded'))
      .catch(() => this.accountState.set('error'));
  }

  loadEntries(): void {
    this.entriesState.set('loading');
    this.ledger
      .fetchEntries(0)
      .then(() => this.entriesState.set('loaded'))
      .catch(() => this.entriesState.set('error'));
  }

  setAmount(value: string): void {
    this.amountInput.set(value);
  }

  async requestFundingInstruction(): Promise<void> {
    if (this.requestingFunding()) {
      return;
    }
    const raw = this.amountInput().trim();
    const amount = Number(raw);
    if (!raw || Number.isNaN(amount) || amount <= 0) {
      this.requestError.set(this.i18n.t('wallet.funding.request_error'));
      return;
    }

    this.requestingFunding.set(true);
    this.requestError.set(null);
    try {
      await this.ledger.requestFundingInstruction({ amount });
      this.amountInput.set('');
    } catch {
      this.requestError.set(this.i18n.t('wallet.funding.request_error'));
    } finally {
      this.requestingFunding.set(false);
    }
  }

  async checkFundingStatus(): Promise<void> {
    const instruction = this.fundingInstruction();
    if (!instruction || this.checkingStatus()) {
      return;
    }
    this.checkingStatus.set(true);
    try {
      await this.ledger.fetchFundingInstruction(instruction.id);
    } finally {
      this.checkingStatus.set(false);
    }
  }

  async nextPage(): Promise<void> {
    this.entriesState.set('loading');
    try {
      await this.ledger.nextEntriesPage();
      this.entriesState.set('loaded');
    } catch {
      this.entriesState.set('error');
    }
  }

  async previousPage(): Promise<void> {
    this.entriesState.set('loading');
    try {
      await this.ledger.previousEntriesPage();
      this.entriesState.set('loaded');
    } catch {
      this.entriesState.set('error');
    }
  }

  get hasNextPage(): boolean {
    return this.entriesSkip() + this.pageSize < this.entriesTotal();
  }

  get hasPreviousPage(): boolean {
    return this.entriesSkip() > 0;
  }

  get rangeStart(): number {
    return this.entriesTotal() === 0 ? 0 : this.entriesSkip() + 1;
  }

  get rangeEnd(): number {
    return Math.min(this.entriesSkip() + this.pageSize, this.entriesTotal());
  }
}
