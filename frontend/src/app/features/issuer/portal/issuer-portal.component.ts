import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';

import { I18nService } from '../../../core/i18n/i18n.service';
import { TPipe } from '../../../core/i18n/t.pipe';
import { ASSET_CLASS_FIELDS, ASSET_CLASS_OPTIONS } from '../../../core/issuer/asset-class-fields';
import { AssetClass, CreateAssetRequest } from '../../../core/issuer/issuer.models';
import { IssuerService } from '../../../core/issuer/issuer.service';
import { CustodianService } from '../../../core/custodian/custodian.service';

interface SelectOption {
  value: string;
  labelKey: string;
}

/** Re-uses `kyc.jurisdiction_option.*` -- the same closed set of jurisdiction labels
 * already shipped for the investor onboarding wizard applies equally to an issuer's
 * jurisdiction of incorporation, so this reads that existing i18n module rather than
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
 * Real Phase 3 issuer portal, replacing the placeholder. Three parts, gated on whether the
 * issuer already has a profile (`IssuerService.profile()`, create-once like
 * `InvestorProfile`):
 *   1. No profile yet -> a create-profile form (`POST /issuers/profile`).
 *   2. Profile exists -> a profile summary card, an asset submission form with
 *      asset-class-specific dynamic fields (`POST /assets`), and a table of the issuer's
 *      own previously-submitted assets (`GET /assets`).
 *
 * The asset form's dynamic fields are intentionally *not* modeled as nested `FormGroup`
 * controls -- `classAttributes` is a plain signal keyed by `AssetClassField.key`, reset
 * whenever `asset_class` changes (mirrors how `KycReviewQueueComponent` tracks its
 * per-row free-text reject reason as signal state rather than a form control). Required
 * dynamic fields are validated manually in `submitAsset()` since they're outside Angular's
 * reactive-forms validity tracking.
 *
 * ★ CONTRACT ASSUMPTION: calls `IssuerService`/`CustodianService`, which target backend
 * `issuers`/`assets`/`custodians` modules that hadn't shipped yet when this was written --
 * see the header comments on `core/issuer/issuer.models.ts` and
 * `core/custodian/custodian.models.ts`.
 */
@Component({
  selector: 'app-issuer-portal',
  standalone: true,
  imports: [
    ReactiveFormsModule,
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
  readonly assetColumns = ['name', 'asset_class', 'custodian_id', 'valuation_amount', 'created_at'];

  readonly selectedAssetClass = signal<AssetClass>('SECURITY');
  readonly dynamicFields = computed(() => ASSET_CLASS_FIELDS[this.selectedAssetClass()]);
  readonly classAttributes = signal<Record<string, string>>({});

  readonly profileSubmitting = signal(false);
  readonly profileError = signal<string | null>(null);
  readonly assetSubmitting = signal(false);
  readonly assetError = signal<string | null>(null);

  readonly profileForm = this.fb.group({
    legal_name: this.fb.control('', [Validators.required]),
    registration_number: this.fb.control('', [Validators.required]),
    jurisdiction: this.fb.control('', [Validators.required]),
    contact_email: this.fb.control('', [Validators.required, Validators.email]),
  });

  readonly assetForm = this.fb.group({
    name: this.fb.control('', [Validators.required]),
    description: this.fb.control('', [Validators.required]),
    asset_class: this.fb.control<AssetClass>('SECURITY', [Validators.required]),
    custodian_id: this.fb.control(0, [Validators.required, Validators.min(1)]),
    valuation_amount: this.fb.control(0, [Validators.required, Validators.min(0)]),
    valuation_currency: this.fb.control('USD', [Validators.required]),
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
    this.classAttributes.set({});
  }

  dynamicFieldValue(key: string): string {
    return this.classAttributes()[key] ?? '';
  }

  setClassAttribute(key: string, event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.classAttributes.update((attrs) => ({ ...attrs, [key]: value }));
  }

  async submitAsset(): Promise<void> {
    if (this.assetForm.invalid || this.hasMissingRequiredDynamicField() || this.assetSubmitting()) {
      this.assetForm.markAllAsTouched();
      return;
    }

    this.assetSubmitting.set(true);
    this.assetError.set(null);
    try {
      const value = this.assetForm.getRawValue();
      const request: CreateAssetRequest = {
        custodian_id: value.custodian_id,
        name: value.name,
        asset_class: value.asset_class,
        description: value.description,
        valuation_amount: value.valuation_amount,
        valuation_currency: value.valuation_currency,
        class_attributes: this.classAttributes(),
      };
      await this.issuerService.createAsset(request);

      this.assetForm.reset({
        name: '',
        description: '',
        asset_class: 'SECURITY',
        custodian_id: 0,
        valuation_amount: 0,
        valuation_currency: 'USD',
      });
      this.selectedAssetClass.set('SECURITY');
      this.classAttributes.set({});
    } catch {
      this.assetError.set(this.i18n.t('issuer.error.generic'));
    } finally {
      this.assetSubmitting.set(false);
    }
  }

  private hasMissingRequiredDynamicField(): boolean {
    return this.dynamicFields().some((field) => field.required && !this.classAttributes()[field.key]?.trim());
  }
}
