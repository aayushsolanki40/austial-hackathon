import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { RouterLink } from '@angular/router';

import { I18nService } from '../../../core/i18n/i18n.service';
import { TPipe } from '../../../core/i18n/t.pipe';
import { ASSET_CLASS_DESCRIPTION_HINTS, ASSET_CLASS_OPTIONS } from '../../../core/issuer/asset-class-fields';
import { Asset, AssetClass, CreateAssetRequest } from '../../../core/issuer/issuer.models';
import { IssuerService } from '../../../core/issuer/issuer.service';
import { CustodianService } from '../../../core/custodian/custodian.service';

interface SelectOption {
  value: string;
  labelKey: string;
}

/** Re-uses `kyc.jurisdiction_option.*` -- the same closed set of jurisdiction labels
 * already shipped for the investor onboarding wizard applies equally to an issuer's
 * jurisdiction of registration, so this reads that existing i18n module rather than
 * duplicating the same five country labels under `issuer.*`. */
const JURISDICTION_OPTIONS: SelectOption[] = [
  { value: 'IN', labelKey: 'kyc.jurisdiction_option.in' },
  { value: 'AE', labelKey: 'kyc.jurisdiction_option.ae' },
  { value: 'SG', labelKey: 'kyc.jurisdiction_option.sg' },
  { value: 'GB', labelKey: 'kyc.jurisdiction_option.gb' },
  { value: 'US', labelKey: 'kyc.jurisdiction_option.us' },
];

type ViewState = 'loading' | 'create-profile' | 'profile';

/**
 * Real Phase 3 issuer portal, calling the real backend `issuers`/`assets`/`custodians`
 * modules (`backend/src/modules/{issuers,assets,custodians}/`). Three parts, gated on
 * whether the issuer already has a profile (`IssuerService.profile()`, create-once like
 * `InvestorProfile`):
 *   1. No profile yet -> a create-profile form (`POST /issuers/profile`).
 *   2. Profile exists -> a profile summary card, an asset submission form (`POST /assets`
 *      -- just `name`/`asset_class`/`description`, the real `CreateAssetDto`), and a table
 *      of the issuer's own previously-submitted assets (`GET /assets`) with a per-row
 *      "attach custodian" action (`POST /assets/:id/custodian`) for assets that aren't yet
 *      `tokenization_ready`.
 *
 * `asset_class` selection no longer drives dynamic form fields (the real `CreateAssetDto`
 * has no `class_attributes` blob) -- it only swaps an i18n hint shown under the description
 * field (`ASSET_CLASS_DESCRIPTION_HINTS`), nudging the issuer toward class-appropriate
 * detail in that one free-text field.
 */
@Component({
  selector: 'app-issuer-portal',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTableModule,
    TPipe,
  ],
  templateUrl: './issuer-portal.component.html',
  styleUrl: './issuer-portal.component.scss',
})
export default class IssuerPortalComponent implements OnInit {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly issuerService = inject(IssuerService);
  private readonly custodianService = inject(CustodianService);
  private readonly i18n = inject(I18nService);

  readonly viewState = signal<ViewState>('loading');
  readonly profile = this.issuerService.profile;
  readonly assets = this.issuerService.assets;
  readonly verifiedCustodians = this.custodianService.verifiedCustodians;

  readonly jurisdictionOptions = JURISDICTION_OPTIONS;
  readonly assetClassOptions = ASSET_CLASS_OPTIONS;
  readonly assetColumns = ['name', 'asset_class', 'status', 'created_at', 'actions'];

  readonly selectedAssetClass = signal<AssetClass>('SECURITY');
  readonly descriptionHintKey = computed(() => ASSET_CLASS_DESCRIPTION_HINTS[this.selectedAssetClass()]);

  readonly profileSubmitting = signal(false);
  readonly profileError = signal<string | null>(null);
  readonly assetSubmitting = signal(false);
  readonly assetError = signal<string | null>(null);

  readonly attachCustodianSelections = signal<Record<number, number>>({});
  readonly attachingAssetId = signal<number | null>(null);

  readonly profileForm = this.fb.group({
    legal_name: this.fb.control('', [Validators.required]),
    registration_number: this.fb.control('', [Validators.required]),
    registration_jurisdiction: this.fb.control('', [Validators.required]),
  });

  readonly assetForm = this.fb.group({
    name: this.fb.control('', [Validators.required]),
    description: this.fb.control('', [Validators.required]),
    asset_class: this.fb.control<AssetClass>('SECURITY', [Validators.required]),
  });

  async ngOnInit(): Promise<void> {
    const profile = await this.issuerService.fetchProfile();
    if (profile) {
      this.viewState.set('profile');
      await Promise.all([this.issuerService.listAssets(), this.custodianService.list()]);
    } else {
      this.viewState.set('create-profile');
    }
  }

  async submitProfile(): Promise<void> {
    if (this.profileForm.invalid || this.profileSubmitting()) {
      this.profileForm.markAllAsTouched();
      return;
    }

    this.profileSubmitting.set(true);
    this.profileError.set(null);
    try {
      await this.issuerService.createProfile(this.profileForm.getRawValue());
      this.viewState.set('profile');
      await Promise.all([this.issuerService.listAssets(), this.custodianService.list()]);
    } catch {
      this.profileError.set(this.i18n.t('issuer.error.generic'));
    } finally {
      this.profileSubmitting.set(false);
    }
  }

  onAssetClassChange(assetClass: AssetClass): void {
    this.selectedAssetClass.set(assetClass);
  }

  async submitAsset(): Promise<void> {
    if (this.assetForm.invalid || this.assetSubmitting()) {
      this.assetForm.markAllAsTouched();
      return;
    }

    this.assetSubmitting.set(true);
    this.assetError.set(null);
    try {
      const value = this.assetForm.getRawValue();
      const request: CreateAssetRequest = {
        name: value.name,
        asset_class: value.asset_class,
        description: value.description,
      };
      await this.issuerService.createAsset(request);

      this.assetForm.reset({
        name: '',
        description: '',
        asset_class: 'SECURITY',
      });
      this.selectedAssetClass.set('SECURITY');
    } catch {
      this.assetError.set(this.i18n.t('issuer.error.generic'));
    } finally {
      this.assetSubmitting.set(false);
    }
  }

  selectedCustodianFor(assetId: number): number | null {
    return this.attachCustodianSelections()[assetId] ?? null;
  }

  setAttachCustodianSelection(assetId: number, custodianId: number): void {
    this.attachCustodianSelections.update((selections) => ({ ...selections, [assetId]: custodianId }));
  }

  async attachCustodian(asset: Asset): Promise<void> {
    const custodianId = this.selectedCustodianFor(asset.id);
    if (!custodianId || this.attachingAssetId() !== null) {
      return;
    }

    this.attachingAssetId.set(asset.id);
    this.assetError.set(null);
    try {
      await this.issuerService.attachCustodian(asset.id, custodianId);
    } catch {
      this.assetError.set(this.i18n.t('issuer.error.generic'));
    } finally {
      this.attachingAssetId.set(null);
    }
  }
}
