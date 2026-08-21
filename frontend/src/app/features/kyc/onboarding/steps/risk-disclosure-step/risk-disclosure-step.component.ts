import { Component, EventEmitter, Output, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { I18nService } from '../../../../../core/i18n/i18n.service';
import { TPipe } from '../../../../../core/i18n/t.pipe';
import { KycService } from '../../../../../core/kyc/kyc.service';

/** Stable identifier for the current risk-disclosure copy shown below, sent as
 * `disclosure_version` on `POST /kyc/submissions/:id/consent`. The backend just stores
 * whatever string is sent -- bump this whenever the disclosure copy changes so a
 * historical acknowledgment stays traceable to the exact text the investor agreed to. */
const DISCLOSURE_VERSION = '2026-08-21-v1';

/**
 * Onboarding wizard step 4: the persisted, timestamped risk-disclosure consent record
 * required before a submission can leave `DRAFT` -- "a persisted acknowledgment row, not
 * a cookie banner." The checkbox itself is only a UI affordance; what matters is that
 * `submit()` calls `KycService.submitConsent()` (`POST /kyc/submissions/:id/consent`) to
 * record the acknowledgment server-side, then `KycService.submit()`
 * (`POST /kyc/submissions/:id/submit`) to finalize the submission.
 *
 * If the wizard resumes here with consent already recorded (`submission()?.consent` is
 * non-`null`, e.g. the investor left and came back after acknowledging but before the
 * final submit went through), the consent call is skipped -- calling it again for the
 * same submission 409s server-side (`kyc.error.consent_already_recorded`).
 */
@Component({
  selector: 'app-kyc-risk-disclosure-step',
  standalone: true,
  imports: [MatButtonModule, MatCheckboxModule, MatProgressSpinnerModule, TPipe],
  templateUrl: './risk-disclosure-step.component.html',
  styleUrl: './risk-disclosure-step.component.scss',
})
export class RiskDisclosureStepComponent {
  private readonly kyc = inject(KycService);
  private readonly i18n = inject(I18nService);

  @Output() readonly completed = new EventEmitter<void>();

  readonly disclosureVersion = DISCLOSURE_VERSION;
  readonly alreadyConsented = !!this.kyc.submission()?.consent;
  readonly acknowledged = signal(this.alreadyConsented);
  readonly submitting = signal(false);
  readonly errorMessage = signal<string | null>(null);

  async submit(): Promise<void> {
    const submissionId = this.kyc.submission()?.id;
    if (!this.acknowledged() || this.submitting() || submissionId == null) {
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set(null);
    try {
      if (!this.kyc.submission()?.consent) {
        await this.kyc.submitConsent(submissionId, this.disclosureVersion);
      }
      await this.kyc.submit(submissionId);
      this.completed.emit();
    } catch {
      this.errorMessage.set(this.i18n.t('kyc.error.generic'));
    } finally {
      this.submitting.set(false);
    }
  }
}
