import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiService } from '../api/api.service';
import { CreateCustodianRequest, Custodian, CustodianListResponse } from './custodian.models';

const CUSTODIAN_PAGE_SIZE = 50;

/**
 * Signal-based custodian-registry state + calls to the real backend `custodians` module
 * (`backend/src/modules/custodians/`). Shared by two very different callers: the issuer
 * portal's asset custodian-attachment flow (read-only, to pick a verified custodian) and the
 * admin issuer/custodian management screen (list + create + verify). Mirrors `KycService`'s
 * pattern -- signals for local list state, `ApiService` for HTTP.
 *
 * Verification is one-directional in this backend -- there is no `POST
 * /custodians/:id/unverify` endpoint, so this service intentionally has no `unverify` method.
 */
@Injectable({ providedIn: 'root' })
export class CustodianService {
  private readonly api = inject(ApiService);

  private readonly custodiansSignal = signal<Custodian[]>([]);
  private readonly loadingSignal = signal(false);

  readonly custodians = this.custodiansSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();

  /** Convenience view for the issuer asset form -- only IFSCA-verified custodians are
   * eligible to be attached to an asset (the build plan's tokenization-gating rule starts
   * here: picking an unverified custodian would just 409 later at attach time). */
  readonly verifiedCustodians = computed(() => this.custodiansSignal().filter((c) => c.ifsca_verified));

  /** `GET /custodians?skip=&take=`. Unwraps `CustodianListDto.items`. */
  async list(): Promise<Custodian[]> {
    this.loadingSignal.set(true);
    try {
      const response = await firstValueFrom(
        this.api.get<CustodianListResponse>('/custodians', { skip: 0, take: CUSTODIAN_PAGE_SIZE }),
      );
      this.custodiansSignal.set(response.items);
      return response.items;
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /** `POST /custodians` -- `COMPLIANCE_OFFICER`-only server-side. */
  async create(request: CreateCustodianRequest): Promise<Custodian> {
    const custodian = await firstValueFrom(this.api.post<Custodian>('/custodians', request));
    this.custodiansSignal.update((custodians) => [...custodians, custodian]);
    return custodian;
  }

  /** `POST /custodians/:id/verify` -- flips `ifsca_verified` to `true`. `COMPLIANCE_OFFICER`-
   * only server-side. Modeled as a dedicated action endpoint (not a generic `PATCH`) to
   * mirror the existing `POST /kyc/submissions/:id/approve` convention this codebase already
   * uses for state-flipping compliance actions. */
  async verify(id: number): Promise<Custodian> {
    const custodian = await firstValueFrom(this.api.post<Custodian>(`/custodians/${id}/verify`));
    this.replace(custodian);
    return custodian;
  }

  private replace(custodian: Custodian): void {
    this.custodiansSignal.update((custodians) => custodians.map((c) => (c.id === custodian.id ? custodian : c)));
  }
}
