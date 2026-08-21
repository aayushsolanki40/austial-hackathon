import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiService } from '../api/api.service';
import { Asset, CreateAssetRequest, CreateIssuerProfileRequest, IssuerProfile } from './issuer.models';

/**
 * Signal-based issuer-profile + own-asset state, calling the (assumed) backend
 * `/issuers`/`/assets` endpoints -- see the ★ CONTRACT ASSUMPTION header on
 * `issuer.models.ts`. Mirrors `KycService`'s shape: signals for local state, `ApiService`
 * for HTTP, consumed by the issuer portal.
 */
@Injectable({ providedIn: 'root' })
export class IssuerService {
  private readonly api = inject(ApiService);

  private readonly profileSignal = signal<IssuerProfile | null>(null);
  private readonly assetsSignal = signal<Asset[]>([]);
  private readonly loadingSignal = signal(false);

  readonly profile = this.profileSignal.asReadonly();
  readonly assets = this.assetsSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();

  /** `GET /issuers/profile`. Like `KycService.fetchProfile`, swallows HTTP errors (404 --
   * no profile yet -- and anything else) and just treats them as "no profile", since the
   * issuer portal's only decision here is "show the create form or the profile view." */
  async fetchProfile(): Promise<IssuerProfile | null> {
    this.loadingSignal.set(true);
    try {
      const profile = await firstValueFrom(this.api.get<IssuerProfile>('/issuers/profile'));
      this.profileSignal.set(profile);
      return profile;
    } catch {
      this.profileSignal.set(null);
      return null;
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /** `POST /issuers/profile` -- create-once, mirrors `InvestorProfile`; a second call is
   * expected to 409 server-side. Callers should check `profile()` first. */
  async createProfile(request: CreateIssuerProfileRequest): Promise<IssuerProfile> {
    const profile = await firstValueFrom(this.api.post<IssuerProfile>('/issuers/profile', request));
    this.profileSignal.set(profile);
    return profile;
  }

  /** `GET /assets` -- assumed scoped to the caller's own issuer (mirrors `GET
   * /kyc/submissions` returning only the authenticated investor's own submissions), not a
   * global asset catalog. */
  async listAssets(): Promise<Asset[]> {
    const assets = await firstValueFrom(this.api.get<Asset[]>('/assets'));
    this.assetsSignal.set(assets);
    return assets;
  }

  /** `POST /assets`. */
  async createAsset(request: CreateAssetRequest): Promise<Asset> {
    const asset = await firstValueFrom(this.api.post<Asset>('/assets', request));
    this.assetsSignal.update((assets) => [asset, ...assets]);
    return asset;
  }
}
