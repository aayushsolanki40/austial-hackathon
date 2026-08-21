import { Component, OnInit, inject, signal } from '@angular/core';
import { MatStepperModule } from '@angular/material/stepper';
import { Router } from '@angular/router';

import { TPipe } from '../../../core/i18n/t.pipe';
import { KycService } from '../../../core/kyc/kyc.service';
import { ONBOARDING_STEP_INDEX, resolveInitialStep } from './onboarding-step.util';
import { DocumentUploadStepComponent } from './steps/document-upload-step/document-upload-step.component';
import { KycStatusStepComponent } from './steps/kyc-status-step/kyc-status-step.component';
import { LivenessStepComponent } from './steps/liveness-step/liveness-step.component';
import { ProfileStepComponent } from './steps/profile-step/profile-step.component';
import { RiskDisclosureStepComponent } from './steps/risk-disclosure-step/risk-disclosure-step.component';

/**
 * Real Phase 2 onboarding wizard, replacing the Phase-1 placeholder. Multi-step Material
 * Stepper: profile -> document upload -> liveness capture -> risk disclosure (signed
 * consent) -> pending/verified status. Each step is its own child component that emits
 * `completed` on success; this component owns step-transition state and decides, on
 * load, which step to resume at (see `resolveInitialStep`) so a returning investor with
 * an in-review or already-verified profile doesn't have to re-walk a finished wizard.
 *
 * `selectedIndex` is the single source of truth for which step is showing, two-way bound
 * to `mat-stepper` (`[selectedIndex]` / `(selectedIndexChange)`) rather than driven via
 * `MatStepper.next()` against a `@ViewChild` -- a template binding that keeps re-pushing
 * a value on every change-detection cycle fights any imperative call that tries to move
 * the stepper independently of that binding, so advancing has to happen by updating this
 * signal, not by calling into the stepper directly.
 *
 * This is also the destination `kycVerifiedGuard` redirects to for any non-`VERIFIED`
 * investor -- see `core/auth/kyc-verified.guard.ts`.
 */
@Component({
  selector: 'app-onboarding',
  standalone: true,
  imports: [
    MatStepperModule,
    TPipe,
    ProfileStepComponent,
    DocumentUploadStepComponent,
    LivenessStepComponent,
    RiskDisclosureStepComponent,
    KycStatusStepComponent,
  ],
  templateUrl: './onboarding.component.html',
  styleUrl: './onboarding.component.scss',
})
export default class OnboardingComponent implements OnInit {
  private readonly kyc = inject(KycService);
  private readonly router = inject(Router);

  readonly stepIndex = ONBOARDING_STEP_INDEX;
  readonly ready = signal(false);
  readonly selectedIndex = signal<number>(ONBOARDING_STEP_INDEX.PROFILE);

  readonly profileDone = signal(false);
  readonly documentsDone = signal(false);
  readonly livenessDone = signal(false);
  readonly disclosureDone = signal(false);

  async ngOnInit(): Promise<void> {
    const profile = await this.kyc.fetchProfile();

    if (profile?.kyc_status === 'VERIFIED') {
      await this.router.navigateByUrl('/');
      return;
    }

    const submission = profile ? await this.kyc.fetchLatestSubmission() : null;

    const initial = resolveInitialStep(profile, submission);
    this.profileDone.set(initial > ONBOARDING_STEP_INDEX.PROFILE);
    this.documentsDone.set(initial > ONBOARDING_STEP_INDEX.DOCUMENTS);
    this.livenessDone.set(initial > ONBOARDING_STEP_INDEX.LIVENESS);
    this.disclosureDone.set(initial > ONBOARDING_STEP_INDEX.DISCLOSURE);

    this.selectedIndex.set(initial);
    this.ready.set(true);
  }

  onProfileCompleted(): void {
    this.profileDone.set(true);
    this.selectedIndex.set(ONBOARDING_STEP_INDEX.DOCUMENTS);
  }

  onDocumentsCompleted(): void {
    this.documentsDone.set(true);
    this.selectedIndex.set(ONBOARDING_STEP_INDEX.LIVENESS);
  }

  onLivenessCompleted(): void {
    this.livenessDone.set(true);
    this.selectedIndex.set(ONBOARDING_STEP_INDEX.DISCLOSURE);
  }

  onDisclosureCompleted(): void {
    this.disclosureDone.set(true);
    this.selectedIndex.set(ONBOARDING_STEP_INDEX.STATUS);
  }
}
