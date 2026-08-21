import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiService } from '../api/api.service';
import {
  Asset,
  AssetListResponse,
  CreateAssetRequest,
  CreateIssuerProfileRequest,
  IssuerProfile,
} from './issuer.models';

const ASSET_PAGE_SIZE = 50;

/**
 * Signal-based issuer-profile + own-asset state, calling the real backend
 * `issuers`/`assets` modules (`backend/src/modules/{issuers,assets}/`). Mirrors
 * `KycService`'s shape: signals for local state, `ApiService` for HTTP, consumed by the
 * issuer portal.
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

  /** `GET /assets?skip=&take=` -- scoped server-side to the caller's own issuer (not a
   * global asset catalog). Unwraps `AssetListDto.items`. */
  async listAssets(): Promise<Asset[]> {
    const response = await firstValueFrom(
      this.api.get<AssetListResponse>('/assets', { skip: 0, take: ASSET_PAGE_SIZE }),
    );
    this.assetsSignal.set(response.items);
    return response.items;
  }

  /** `POST /assets`. */
  async createAsset(request: CreateAssetRequest): Promise<Asset> {
    const asset = await firstValueFrom(this.api.post<Asset>('/assets', request));
    this.assetsSignal.update((assets) => [asset, ...assets]);
    return asset;
  }

  /** `POST /assets/:id/custodian` -- attaches an IFSCA-verified custodian to a previously
   * submitted asset, flipping `custodian_verified`/`tokenization_ready` to `true` in the
   * response. 409s server-side if the chosen custodian isn't `ifsca_verified`. */
  async attachCustodian(assetId: number, custodianId: number): Promise<Asset> {
    const asset = await firstValueFrom(
      this.api.post<Asset>(`/assets/${assetId}/custodian`, { custodian_id: custodianId }),
    );
    this.assetsSignal.update((assets) => assets.map((a) => (a.id === asset.id ? asset : a)));
    return asset;
  }
}
