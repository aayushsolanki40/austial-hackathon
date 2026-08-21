import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiService } from '../api/api.service';
import { CreateCustodianRequest, Custodian } from './custodian.models';

/**
 * Signal-based custodian-registry state + calls to the (assumed) backend `/custodians`
 * endpoints. Shared by two very different callers: the issuer portal's asset submission
 * form (read-only, to pick a custodian for `Asset.custodian_id`) and the admin
 * issuer/custodian management screen (list + create + verify/unverify). Mirrors
 * `KycService`'s pattern -- signals for local list state, `ApiService` for HTTP.
 */
@Injectable({ providedIn: 'root' })
export class CustodianService {
  private readonly api = inject(ApiService);

  private readonly custodiansSignal = signal<Custodian[]>([]);
  private readonly loadingSignal = signal(false);

  readonly custodians = this.custodiansSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();

  /** Convenience view for the issuer asset form -- only IFSCA-verified custodians are
   * eligible to be attached to a new asset (the build plan's tokenization-gating rule
   * starts here: picking an unverified custodian would just fail later at issuance). */
  readonly verifiedCustodians = computed(() => this.custodiansSignal().filter((c) => c.ifsca_verified));

  /** `GET /custodians`. */
  async list(): Promise<Custodian[]> {
    this.loadingSignal.set(true);
    try {
      const custodians = await firstValueFrom(this.api.get<Custodian[]>('/custodians'));
      this.custodiansSignal.set(custodians);
      return custodians;
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /** `POST /custodians` -- assumed `COMPLIANCE_OFFICER`/`ADMIN`-gated server-side. */
  async create(request: CreateCustodianRequest): Promise<Custodian> {
    const custodian = await firstValueFrom(this.api.post<Custodian>('/custodians', request));
    this.custodiansSignal.update((custodians) => [...custodians, custodian]);
    return custodian;
  }

  /** `POST /custodians/:id/verify` -- flips `ifsca_verified` to `true`. Modeled as a
   * dedicated action endpoint (not a generic `PATCH`) to mirror the existing
   * `POST /kyc/submissions/:id/approve` convention this codebase already uses for
   * state-flipping compliance actions. */
  async verify(id: number): Promise<Custodian> {
    const custodian = await firstValueFrom(this.api.post<Custodian>(`/custodians/${id}/verify`));
    this.replace(custodian);
    return custodian;
  }

  /** `POST /custodians/:id/unverify` -- flips `ifsca_verified` back to `false`, e.g. after
   * an IFSCA registration lapses. The admin screen's "flip status" action calls whichever
   * of `verify`/`unverify` is the opposite of the row's current state. */
  async unverify(id: number): Promise<Custodian> {
    const custodian = await firstValueFrom(this.api.post<Custodian>(`/custodians/${id}/unverify`));
    this.replace(custodian);
    return custodian;
  }

  private replace(custodian: Custodian): void {
    this.custodiansSignal.update((custodians) => custodians.map((c) => (c.id === custodian.id ? custodian : c)));
  }
}
