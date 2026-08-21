import { Injectable, inject, signal } from '@angular/core';
import { Observable, firstValueFrom } from 'rxjs';

import { ApiService } from '../api/api.service';
import {
  CreateDistributionRequest,
  CreateRedemptionRequest,
  Distribution,
  DistributionListResponse,
  DistributionStatus,
  ProcessDistributionResult,
  RedemptionRequest,
  RedemptionRequestListResponse,
  RedemptionStatus,
} from './redemptions.models';

const PAGE_SIZE = 50;

/**
 * Signal-based state + `ApiService` calls, mirroring `SubscriptionsService`'s established shape.
 * Real routes (`redemptions_controller.py`) span three audiences the backend itself splits into
 * three route families -- kept in one service, like the controller keeps them in one class:
 *   - investor-facing (`/redemptions`, `/redemptions/mine...`) -- request/view/cancel own requests.
 *   - ops-facing (`/redemptions`, `/redemptions/:id/...`) -- review queue + state-machine actions.
 *   - distributions (`/redemptions/distributions...`) -- create/list/process, nested under the
 *     same controller per the real backend route layout.
 */
@Injectable({ providedIn: 'root' })
export class RedemptionsService {
  private readonly api = inject(ApiService);

  private readonly myRedemptionsSignal = signal<RedemptionRequest[]>([]);
  private readonly currentSignal = signal<RedemptionRequest | null>(null);
  private readonly queueSignal = signal<RedemptionRequest[]>([]);
  private readonly distributionsSignal = signal<Distribution[]>([]);
  private readonly seriesDistributionsSignal = signal<Distribution[]>([]);
  private readonly loadingSignal = signal(false);

  readonly myRedemptions = this.myRedemptionsSignal.asReadonly();
  readonly current = this.currentSignal.asReadonly();
  readonly queue = this.queueSignal.asReadonly();
  readonly distributions = this.distributionsSignal.asReadonly();
  readonly seriesDistributions = this.seriesDistributionsSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();

  // -- investor-facing: request / view / cancel ----------------------------------------------

  /** `POST /redemptions`. Prepends the new request to `myRedemptions` and sets `current`. */
  async create(request: CreateRedemptionRequest): Promise<RedemptionRequest> {
    const redemption = await firstValueFrom(this.api.post<RedemptionRequest>('/redemptions', request));
    this.myRedemptionsSignal.update((requests) => [redemption, ...requests]);
    this.currentSignal.set(redemption);
    return redemption;
  }

  /** `GET /redemptions/mine?skip=&take=`. Unwraps `{ total, items }`. */
  async listMine(): Promise<RedemptionRequest[]> {
    this.loadingSignal.set(true);
    try {
      const response = await firstValueFrom(
        this.api.get<RedemptionRequestListResponse>('/redemptions/mine', { skip: 0, take: PAGE_SIZE }),
      );
      this.myRedemptionsSignal.set(response.items);
      return response.items;
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /** `GET /redemptions/mine/:id`. Sets `current`. */
  async fetchMine(id: number): Promise<RedemptionRequest> {
    const redemption = await firstValueFrom(this.api.get<RedemptionRequest>(`/redemptions/mine/${id}`));
    this.currentSignal.set(redemption);
    return redemption;
  }

  /** `POST /redemptions/mine/:id/cancel` -- `REQUESTED` only per the backend's
   * `ALLOWED_TRANSITIONS`. Patches the request in place in `myRedemptions`/`current`. */
  async cancelMine(id: number): Promise<RedemptionRequest> {
    const redemption = await firstValueFrom(this.api.post<RedemptionRequest>(`/redemptions/mine/${id}/cancel`));
    this.myRedemptionsSignal.update((requests) => requests.map((r) => (r.id === id ? redemption : r)));
    if (this.currentSignal()?.id === id) {
      this.currentSignal.set(redemption);
    }
    return redemption;
  }

  // -- ops-facing: review queue -----------------------------------------------------------------

  /** `GET /redemptions?status=&skip=&take=`. */
  async listQueue(status?: RedemptionStatus): Promise<RedemptionRequest[]> {
    this.loadingSignal.set(true);
    try {
      const response = await firstValueFrom(
        this.api.get<RedemptionRequestListResponse>('/redemptions', { status, skip: 0, take: PAGE_SIZE }),
      );
      this.queueSignal.set(response.items);
      return response.items;
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /** `POST /redemptions/:id/approve` -- `REQUESTED -> COMPLIANCE_APPROVED`. */
  async approve(id: number): Promise<RedemptionRequest> {
    return this.mutateQueued(id, () => this.api.post<RedemptionRequest>(`/redemptions/${id}/approve`));
  }

  /** `POST /redemptions/:id/reject` -- `REQUESTED -> REJECTED`. */
  async reject(id: number, reason: string): Promise<RedemptionRequest> {
    return this.mutateQueued(id, () => this.api.post<RedemptionRequest>(`/redemptions/${id}/reject`, { reason }));
  }

  /** `POST /redemptions/:id/release` -- `COMPLIANCE_APPROVED -> CUSTODIAN_RELEASED`. */
  async release(id: number): Promise<RedemptionRequest> {
    return this.mutateQueued(id, () => this.api.post<RedemptionRequest>(`/redemptions/${id}/release`));
  }

  /** `POST /redemptions/:id/complete` -- `CUSTODIAN_RELEASED -> COMPLETED`. Produces the payout. */
  async complete(id: number): Promise<RedemptionRequest> {
    return this.mutateQueued(id, () => this.api.post<RedemptionRequest>(`/redemptions/${id}/complete`));
  }

  private async mutateQueued(id: number, action: () => Observable<RedemptionRequest>): Promise<RedemptionRequest> {
    const redemption = await firstValueFrom(action());
    this.queueSignal.update((requests) => requests.map((r) => (r.id === id ? redemption : r)));
    return redemption;
  }

  // -- distributions -----------------------------------------------------------------------------

  /** `POST /redemptions/distributions` (ops-only). Prepends the new distribution to
   * `distributions`. */
  async createDistribution(request: CreateDistributionRequest): Promise<Distribution> {
    const distribution = await firstValueFrom(this.api.post<Distribution>('/redemptions/distributions', request));
    this.distributionsSignal.update((distributions) => [distribution, ...distributions]);
    return distribution;
  }

  /** `GET /redemptions/distributions?status=&skip=&take=` -- open to any authenticated role. */
  async listDistributions(status?: DistributionStatus): Promise<Distribution[]> {
    const response = await firstValueFrom(
      this.api.get<DistributionListResponse>('/redemptions/distributions', { status, skip: 0, take: PAGE_SIZE }),
    );
    this.distributionsSignal.set(response.items);
    return response.items;
  }

  /** `GET /redemptions/distributions/token-series/:series_id?skip=&take=` -- open to any
   * authenticated role; backs the investor-facing distribution history for a held series. */
  async listDistributionsForSeries(seriesId: number): Promise<Distribution[]> {
    const response = await firstValueFrom(
      this.api.get<DistributionListResponse>(`/redemptions/distributions/token-series/${seriesId}`, { skip: 0, take: PAGE_SIZE }),
    );
    this.seriesDistributionsSignal.set(response.items);
    return response.items;
  }

  /** `POST /redemptions/distributions/:id/process` (ops-only) -- `DRAFT` only. Runs the pro-rata
   * payout batch synchronously and returns the result; also flips the distribution's status to
   * `COMPLETED` in place in `distributions`. */
  async processDistribution(id: number): Promise<ProcessDistributionResult> {
    const result = await firstValueFrom(this.api.post<ProcessDistributionResult>(`/redemptions/distributions/${id}/process`));
    this.distributionsSignal.update((distributions) =>
      distributions.map((d) => (d.id === id ? { ...d, status: 'COMPLETED', processed_at: new Date().toISOString() } : d)),
    );
    return result;
  }
}
