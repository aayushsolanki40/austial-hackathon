import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router } from '@angular/router';

import { TPipe } from '../../../../../core/i18n/t.pipe';
import { KycService } from '../../../../../core/kyc/kyc.service';

/**
 * Onboarding wizard's final step: surfaces the investor's current `KycSubmission.status`
 * (the granular `SUBMITTED -> AUTO_SCREENING -> MANUAL_REVIEW -> VERIFIED | REJECTED`
 * machine) with a status-appropriate message, plus the rejection reason
 * (`submission.review_notes`) when rejected. `kycVerifiedGuard` -- gated on the coarser
 * `InvestorProfile.kyc_status` -- is the actual gate on the rest of the app; this step is
 * what an investor sees while waiting on it, plus a manual refresh so they don't have to
 * reload the page to notice a status change.
 */
@Component({
  selector: 'app-kyc-status-step',
  standalone: true,
  imports: [MatButtonModule, MatProgressSpinnerModule, TPipe],
  templateUrl: './kyc-status-step.component.html',
  styleUrl: './kyc-status-step.component.scss',
})
export class KycStatusStepComponent {
  private readonly kyc = inject(KycService);
  private readonly router = inject(Router);

  readonly submission = this.kyc.submission;
  readonly isVerified = this.kyc.isVerified;
  readonly isRejected = this.kyc.isRejected;
  readonly refreshing = signal(false);

  async refresh(): Promise<void> {
    this.refreshing.set(true);
    try {
      await this.kyc.fetchProfile();
      await this.kyc.fetchLatestSubmission();
    } finally {
      this.refreshing.set(false);
    }
  }

  async goToDashboard(): Promise<void> {
    await this.router.navigateByUrl('/');
  }
}
