import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { RouterLink } from '@angular/router';

import { TPipe } from '../../core/i18n/t.pipe';
import { HoldingsService } from '../../core/holdings/holdings.service';
import { IN_FLIGHT_SUBSCRIPTION_STATUSES, SubscriptionsService } from '../../core/subscriptions/subscriptions.service';

type LoadState = 'loading' | 'error' | 'loaded';

/**
 * Phase 6 portfolio dashboard: the investor's `Holding`s (allocated subscriptions) plus
 * subscriptions still in flight (`PENDING`/`FUNDED`/`CONFIRMED`, per the build plan's exact
 * wording) -- the two together close the Phase 6 MVP loop end-to-end
 * ("discover -> subscribe -> get allocated -> see a holding"). `ALLOCATED`/`REFUNDED`/
 * `CANCELLED` subscriptions are intentionally left out of the in-flight table: `ALLOCATED` ones
 * have already become a row in `holdings` (shown there instead, not duplicated), and
 * `REFUNDED`/`CANCELLED` are terminal with nothing actionable left to show here.
 */
@Component({
  selector: 'app-portfolio',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, MatButtonModule, MatProgressSpinnerModule, MatTableModule, RouterLink, TPipe],
  templateUrl: './portfolio.component.html',
  styleUrl: './portfolio.component.scss',
})
export default class PortfolioComponent implements OnInit {
  private readonly holdingsService = inject(HoldingsService);
  private readonly subscriptionsService = inject(SubscriptionsService);

  readonly state = signal<LoadState>('loading');
  readonly holdings = this.holdingsService.myHoldings;
  readonly subscriptions = this.subscriptionsService.mySubscriptions;
  readonly inFlightSubscriptions = computed(() =>
    this.subscriptions().filter((s) => IN_FLIGHT_SUBSCRIPTION_STATUSES.includes(s.status)),
  );

  readonly holdingColumns = ['symbol', 'quantity', 'avg_cost_usd', 'status', 'created_at', 'actions'];
  readonly subscriptionColumns = ['symbol', 'units', 'amount_usd', 'status', 'created_at'];

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    Promise.all([this.holdingsService.listMine(), this.subscriptionsService.listMine()])
      .then(() => this.state.set('loaded'))
      .catch(() => this.state.set('error'));
  }
}
