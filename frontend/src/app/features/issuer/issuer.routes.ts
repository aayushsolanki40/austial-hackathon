import { Routes } from '@angular/router';

/**
 * Issuer portal shell. `portal` (Phase 3) handles issuer-profile + asset submission;
 * `proposals`/`proposals/:id` (Phase 4) handle the tokenization-proposal workflow that
 * follows once an asset is `tokenization_ready` -- a sibling area rather than a section
 * bolted onto the portal, see `features/issuer/proposals/issuer-proposals.component.ts`.
 */
export default [
  { path: '', loadComponent: () => import('./portal/issuer-portal.component') },
  { path: 'proposals', loadComponent: () => import('./proposals/issuer-proposals.component') },
  { path: 'proposals/:id', loadComponent: () => import('./proposals/proposal-detail.component') },
] satisfies Routes;
