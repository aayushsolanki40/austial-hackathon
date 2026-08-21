import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiService } from '../api/api.service';
import { Holding, HoldingListResponse } from './holdings.models';

const HOLDING_PAGE_SIZE = 50;

/**
 * Signal-based state + `ApiService` calls, mirroring `SubscriptionsService`'s shape. Real routes
 * (`holdings_controller.py`):
 *   - `GET /holdings/mine?skip=&take=` -- the investor's own holdings.
 *   - `GET /holdings/mine/:id` -- single lookup, backing `/holdings/:id`.
 */
@Injectable({ providedIn: 'root' })
export class HoldingsService {
  private readonly api = inject(ApiService);

  private readonly myHoldingsSignal = signal<Holding[]>([]);
  private readonly currentSignal = signal<Holding | null>(null);
  private readonly loadingSignal = signal(false);

  readonly myHoldings = this.myHoldingsSignal.asReadonly();
  readonly current = this.currentSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();

  /** `GET /holdings/mine?skip=&take=`. Unwraps `{ total, items }`. */
  async listMine(): Promise<Holding[]> {
    this.loadingSignal.set(true);
    try {
      const response = await firstValueFrom(this.api.get<HoldingListResponse>('/holdings/mine', { skip: 0, take: HOLDING_PAGE_SIZE }));
      this.myHoldingsSignal.set(response.items);
      return response.items;
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /** `GET /holdings/mine/:id`. Sets `current`. */
  async fetchMine(id: number): Promise<Holding> {
    const holding = await firstValueFrom(this.api.get<Holding>(`/holdings/mine/${id}`));
    this.currentSignal.set(holding);
    return holding;
  }
}
