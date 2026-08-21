import { Routes } from '@angular/router';

/**
 * Phase 2 onboarding wizard: profile -> documents -> liveness -> risk
 * disclosure -> pending/verified status, all within a single Material
 * Stepper hosted by `OnboardingComponent` at `/onboarding` (see
 * `app.routes.ts`).
 */
export default [
  { path: '', loadComponent: () => import('./onboarding/onboarding.component') },
] satisfies Routes;
