import { Routes } from '@angular/router';

/**
 * Issuer portal shell -- Phase 3/4 will grow this with the asset submission
 * form and issuance-status views. One placeholder route for now.
 */
export default [
  { path: '', loadComponent: () => import('./portal/issuer-portal.component') },
] satisfies Routes;
