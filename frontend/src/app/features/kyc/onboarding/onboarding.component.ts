import { Component } from '@angular/core';

import { PlaceholderPageComponent } from '../../../shared/placeholder-page/placeholder-page.component';

/**
 * Placeholder for the Phase 2 multi-step onboarding wizard (Material
 * Stepper: profile -> document upload -> liveness capture -> risk
 * disclosure with signed consent -> pending/verified state). Wired at
 * `/onboarding` now purely so the route exists for `authGuard`-gated
 * navigation; real content ships with Phase 2.
 */
@Component({
  selector: 'app-onboarding',
  standalone: true,
  imports: [PlaceholderPageComponent],
  template: `<app-placeholder-page titleKey="kyc.onboarding.title" messageKey="kyc.onboarding.placeholder" />`,
})
export default class OnboardingComponent {}
