import { Component, OnInit, inject, signal } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { TPipe } from '../../core/i18n/t.pipe';
import { HoldingsService } from '../../core/holdings/holdings.service';

type LoadState = 'loading' | 'error' | 'loaded';

/** Phase 6 holding detail (`/holdings/:id`) -- the final step of the MVP loop: "an investor
 * can discover an asset, subscribe, get allocated, and see a holding." */
@Component({
  selector: 'app-holding-detail',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, RouterLink, TPipe],
  templateUrl: './holding-detail.component.html',
  styleUrl: './holding-detail.component.scss',
})
export default class HoldingDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly holdingsService = inject(HoldingsService);

  readonly state = signal<LoadState>('loading');
  readonly holding = this.holdingsService.current;

  private get holdingId(): number {
    return Number(this.route.snapshot.paramMap.get('id'));
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.state.set('loading');
    this.holdingsService
      .fetchMine(this.holdingId)
      .then(() => this.state.set('loaded'))
      .catch(() => this.state.set('error'));
  }
}
