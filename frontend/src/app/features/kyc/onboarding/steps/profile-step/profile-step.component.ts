import { Component, EventEmitter, Output, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { I18nService } from '../../../../../core/i18n/i18n.service';
import { TPipe } from '../../../../../core/i18n/t.pipe';
import { InvestorType, RiskProfile } from '../../../../../core/kyc/kyc.models';
import { KycService } from '../../../../../core/kyc/kyc.service';

interface SelectOption {
  value: string;
  labelKey: string;
}

const INVESTOR_TYPE_OPTIONS: SelectOption[] = [
  { value: 'INDIVIDUAL', labelKey: 'kyc.investor_type_option.individual' },
  { value: 'INSTITUTIONAL', labelKey: 'kyc.investor_type_option.institutional' },
];

const RISK_PROFILE_OPTIONS: SelectOption[] = [
  { value: 'CONSERVATIVE', labelKey: 'kyc.risk_profile_option.conservative' },
  { value: 'MODERATE', labelKey: 'kyc.risk_profile_option.moderate' },
  { value: 'AGGRESSIVE', labelKey: 'kyc.risk_profile_option.aggressive' },
];

const JURISDICTION_OPTIONS: SelectOption[] = [
  { value: 'IN', labelKey: 'kyc.jurisdiction_option.in' },
  { value: 'AE', labelKey: 'kyc.jurisdiction_option.ae' },
  { value: 'SG', labelKey: 'kyc.jurisdiction_option.sg' },
  { value: 'GB', labelKey: 'kyc.jurisdiction_option.gb' },
  { value: 'US', labelKey: 'kyc.jurisdiction_option.us' },
];

/**
 * Onboarding wizard step 1: collects both the investor *classification* (investor type,
 * jurisdiction, risk profile -- `POST /investors/profile`, `CreateInvestorProfileDto`)
 * and the identity fields needed to start a `KycSubmission` (legal name, date of birth,
 * nationality -- `POST /kyc/submissions`, `CreateKycSubmissionDto`). Both live on
 * different backend resources but are collected together here since every later step
 * (documents/consent/submit) needs a submission `id`, so this step must produce one
 * before it can complete.
 *
 * `InvestorProfile` is create-once (a second `POST /investors/profile` 409s), so profile
 * creation is skipped entirely if `KycService.profile()` already has one -- this step is
 * only ever shown when the profile and/or the submission is still missing (see
 * `resolveInitialStep`), so "profile already exists, no submission yet" is a real case
 * this has to handle without re-POSTing the profile.
 */
@Component({
  selector: 'app-kyc-profile-step',
  standalone: true,
  imports: [ReactiveFormsModule, TPipe],
  templateUrl: './profile-step.component.html',
  styleUrl: './profile-step.component.scss',
})
export class ProfileStepComponent {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly kyc = inject(KycService);
  private readonly i18n = inject(I18nService);

  @Output() readonly completed = new EventEmitter<void>();

  readonly investorTypeOptions = INVESTOR_TYPE_OPTIONS;
  readonly riskProfileOptions = RISK_PROFILE_OPTIONS;
  readonly jurisdictionOptions = JURISDICTION_OPTIONS;

  readonly submitting = signal(false);
  readonly errorMessage = signal<string | null>(null);

  readonly form = this.fb.group({
    investor_type: this.fb.control('', [Validators.required]),
    jurisdiction: this.fb.control('', [Validators.required]),
    risk_profile: this.fb.control('', [Validators.required]),
    legal_name: this.fb.control('', [Validators.required]),
    date_of_birth: this.fb.control('', [Validators.required]),
    nationality: this.fb.control('', [Validators.required]),
  });

  constructor() {
    const existing = this.kyc.profile();
    if (existing) {
      this.form.patchValue({
        investor_type: existing.investor_type ?? '',
        jurisdiction: existing.jurisdiction ?? '',
        risk_profile: existing.risk_profile ?? '',
      });
      // Profile fields are already saved server-side (create-once) -- disable them
      // rather than let the investor edit values that won't be re-submitted.
      this.form.controls.investor_type.disable();
      this.form.controls.jurisdiction.disable();
      this.form.controls.risk_profile.disable();
    }
  }

  async submit(): Promise<void> {
    if (this.form.invalid || this.submitting()) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set(null);
    try {
      const value = this.form.getRawValue();

      if (!this.kyc.profile()) {
        await this.kyc.createProfile({
          investor_type: value.investor_type as InvestorType,
          jurisdiction: value.jurisdiction,
          risk_profile: value.risk_profile as RiskProfile,
        });
      }

      await this.kyc.createSubmission({
        legal_name: value.legal_name,
        date_of_birth: value.date_of_birth,
        nationality: value.nationality,
      });

      this.completed.emit();
    } catch (error: any) {
      const message =
        error?.userMessage ||
        error?.error?.message ||
        this.i18n.t('kyc.error.generic');
      this.errorMessage.set(message);
    } finally {
      this.submitting.set(false);
    }
  }
}
