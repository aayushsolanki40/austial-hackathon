import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiService } from '../api/api.service';
import { CreateSubscriptionRequest, Subscription, SubscriptionListResponse } from './subscriptions.models';

const SUBSCRIPTION_PAGE_SIZE = 50;

/** In-flight statuses per the Phase 6 state machine -- not yet a `Holding`, still worth
 * surfacing on the portfolio dashboard per the build plan ("subscriptions in flight
 * (PENDING/FUNDED/CONFIRMED)"). */
export const IN_FLIGHT_SUBSCRIPTION_STATUSES: readonly Subscription['status'][] = ['PENDING', 'FUNDED', 'CONFIRMED'];

/**
 * Signal-based state + `ApiService` calls, mirroring `LedgerService`/`IssuanceService`'s
 * established shape. Real routes (`subscriptions_controller.py`):
 *   - `POST /subscriptions` -- create, locking funds in `LedgerAccount.locked_balance`
 *     server-side (the Phase 6 state machine's `PENDING` entry point).
 *   - `GET /subscriptions/mine?skip=&take=` -- the caller's own subscriptions.
 *   - `GET /subscriptions/mine/:id` -- single lookup.
 *   - `POST /subscriptions/mine/:id/cancel` -- investor-initiated cancel.
 */
@Injectable({ providedIn: 'root' })
export class SubscriptionsService {
  private readonly api = inject(ApiService);

  private readonly mySubscriptionsSignal = signal<Subscription[]>([]);
  private readonly currentSignal = signal<Subscription | null>(null);
  private readonly loadingSignal = signal(false);

  readonly mySubscriptions = this.mySubscriptionsSignal.asReadonly();
  readonly current = this.currentSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();

  /** `POST /subscriptions`. Prepends the new subscription to `mySubscriptions` and sets
   * `current` so the subscribe-flow success screen can render it without a refetch. */
  async create(request: CreateSubscriptionRequest): Promise<Subscription> {
    const subscription = await firstValueFrom(this.api.post<Subscription>('/subscriptions', request));
    this.mySubscriptionsSignal.update((subscriptions) => [subscription, ...subscriptions]);
    this.currentSignal.set(subscription);
    return subscription;
  }

  /** `GET /subscriptions/mine?skip=&take=`. Unwraps `{ total, items }`. */
  async listMine(): Promise<Subscription[]> {
    this.loadingSignal.set(true);
    try {
      const response = await firstValueFrom(
        this.api.get<SubscriptionListResponse>('/subscriptions/mine', { skip: 0, take: SUBSCRIPTION_PAGE_SIZE }),
      );
      this.mySubscriptionsSignal.set(response.items);
      return response.items;
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /** `GET /subscriptions/mine/:id`. Sets `current`. */
  async fetchMine(id: number): Promise<Subscription> {
    const subscription = await firstValueFrom(this.api.get<Subscription>(`/subscriptions/mine/${id}`));
    this.currentSignal.set(subscription);
    return subscription;
  }

  /** `POST /subscriptions/mine/:id/cancel`. Patches the subscription in place in
   * `mySubscriptions`/`current` with the server's response rather than removing it locally --
   * `CANCELLED` is a terminal status still worth showing, not a deletion. */
  async cancel(id: number): Promise<Subscription> {
    const subscription = await firstValueFrom(this.api.post<Subscription>(`/subscriptions/mine/${id}/cancel`));
    this.mySubscriptionsSignal.update((subscriptions) => subscriptions.map((s) => (s.id === id ? subscription : s)));
    if (this.currentSignal()?.id === id) {
      this.currentSignal.set(subscription);
    }
    return subscription;
  }
}
