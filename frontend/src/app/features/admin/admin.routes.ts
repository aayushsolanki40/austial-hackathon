import { Routes } from '@angular/router';

import { roleGuard } from '../../core/auth/role.guard';
import AdminShellComponent from './admin-shell/admin-shell.component';

/**
 * Consolidated back-office surface (Section 1.5 of the build plan). The
 * parent `/admin` route is already gated to `roleGuard(['COMPLIANCE_OFFICER',
 * 'ADMIN'])` in `app.routes.ts`; `users` (role/account changes -- an
 * access-control action, not a compliance one) is tightened further to
 * ADMIN-only here. `kyc-review`/`issuers-custodians` are tightened the other
 * way, to COMPLIANCE_OFFICER-only: their backing endpoints
 * (`KycController`'s `review-queue`/`approve`/`reject`,
 * `IssuersController`'s `review-queue`/`approve`/`reject`) are
 * `@Roles("COMPLIANCE_OFFICER")` only on the backend, unlike every other
 * section here which is shared `(COMPLIANCE_OFFICER, ADMIN)` -- an ADMIN
 * reaching these pages would 403 on every call.
 */
export default [
  {
    path: '',
    component: AdminShellComponent,
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { path: 'dashboard', loadComponent: () => import('./dashboard/admin-dashboard.component') },
      {
        path: 'users',
        canActivate: [roleGuard(['ADMIN'])],
        loadComponent: () => import('./users/user-management.component'),
      },
      {
        path: 'kyc-review',
        canActivate: [roleGuard(['COMPLIANCE_OFFICER'])],
        loadComponent: () => import('./kyc-review/kyc-review-queue.component'),
      },
      {
        path: 'issuers-custodians',
        canActivate: [roleGuard(['COMPLIANCE_OFFICER'])],
        loadComponent: () => import('./issuers-custodians/issuer-custodian-admin.component'),
      },
      {
        path: 'issuance-pipeline',
        loadComponent: () => import('./issuance-pipeline/issuance-pipeline.component'),
      },
      {
        path: 'issuance-pipeline/:id',
        loadComponent: () => import('./issuance-pipeline/proposal-review.component'),
      },
      {
        path: 'valuation-oracle',
        loadComponent: () => import('./valuation-oracle/valuation-oracle-admin.component'),
      },
      { path: 'redemptions', loadComponent: () => import('./redemptions-queue/redemption-approval.component') },
      { path: 'compliance', loadComponent: () => import('./compliance/aml-alert-queue.component') },
      { path: 'compliance/reports', loadComponent: () => import('./compliance/report-generator.component') },
      {
        path: 'audit-log',
        canActivate: [roleGuard(['ADMIN', 'COMPLIANCE_OFFICER'])],
        loadComponent: () => import('./audit-log/audit-log-viewer.component'),
      },
    ],
  },
] satisfies Routes;
