import { Routes } from '@angular/router';

import { authGuard } from './core/auth/auth.guard';
import { kycVerifiedGuard } from './core/auth/kyc-verified.guard';
import { roleGuard } from './core/auth/role.guard';

/**
 * Top-level route tree per `AUSTIAL_BUILD_PLAN.md` Section 3. Every branch
 * except `admin` is a placeholder shell today (see each feature's own
 * routes file for what's stubbed vs. real) -- routing exists ahead of the
 * owning phase so guards/navigation can be exercised end-to-end now.
 */
export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./features/auth/login/login.component') },
  { path: 'register', loadComponent: () => import('./features/auth/register/register.component') },

  {
    path: 'onboarding',
    canActivate: [authGuard],
    loadChildren: () => import('./features/kyc/kyc.routes'),
  },

  {
    path: '',
    canActivate: [authGuard, kycVerifiedGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'marketplace' },
      { path: 'marketplace', loadComponent: () => import('./features/marketplace/marketplace.component') },
      { path: 'assets/:id', loadComponent: () => import('./features/marketplace/asset-detail.component') },
      {
        path: 'assets/:id/subscribe',
        loadComponent: () => import('./features/marketplace/asset-subscribe.component'),
      },
      { path: 'portfolio', loadComponent: () => import('./features/portfolio/portfolio.component') },
      { path: 'holdings/:id', loadComponent: () => import('./features/portfolio/holding-detail.component') },
      {
        path: 'holdings/:id/redeem',
        loadComponent: () => import('./features/portfolio/holding-redeem.component'),
      },
      { path: 'wallet', loadComponent: () => import('./features/wallet/wallet.component') },
    ],
  },

  {
    path: 'issuer',
    canActivate: [authGuard, roleGuard(['ISSUER'])],
    loadChildren: () => import('./features/issuer/issuer.routes'),
  },

  {
    path: 'admin',
    canActivate: [authGuard, roleGuard(['COMPLIANCE_OFFICER', 'ADMIN'])],
    loadChildren: () => import('./features/admin/admin.routes'),
  },

  { path: '**', redirectTo: 'marketplace' },
];
