import { Routes } from '@angular/router';

/**
 * Phase 2 will grow this into a multi-step wizard (profile -> documents ->
 * liveness -> risk disclosure). For now, a single placeholder route keeps
 * `/onboarding` (see `app.routes.ts`) resolvable.
 */
export default [
  { path: '', loadComponent: () => import('./onboarding/onboarding.component') },
] satisfies Routes;
