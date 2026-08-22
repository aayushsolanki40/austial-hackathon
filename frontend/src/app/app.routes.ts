import { Routes } from '@angular/router';

import { authGuard } from './core/auth/auth.guard';
import { kycVerifiedGuard } from './core/auth/kyc-verified.guard';
import { roleGuard } from './core/auth/role.guard';

/**
 * Top-level route tree. Landing page is public, authenticated routes require auth guards.
 */
export const routes: Routes = [
  // Public routes
  { path: '', pathMatch: 'full', redirectTo: 'home' },
  { path: 'home', loadComponent: () => import('./features/landing/landing.component').then(m => m.LandingComponent) },
  { path: 'login', loadComponent: () => import('./features/auth/login/login.component') },
  { path: 'register', loadComponent: () => import('./features/auth/register/register.component') },

  // KYC onboarding (auth required)
  {
    path: 'onboarding',
    canActivate: [authGuard],
    loadChildren: () => import('./features/kyc/kyc.routes'),
  },

  // Authenticated app routes (auth + KYC verified required)
  {
    path: 'app',
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

  // Issuer portal
  {
    path: 'issuer',
    canActivate: [authGuard, roleGuard(['ISSUER'])],
    loadChildren: () => import('./features/issuer/issuer.routes'),
  },

  // Admin panel
  {
    path: 'admin',
    canActivate: [authGuard, roleGuard(['COMPLIANCE_OFFICER', 'ADMIN'])],
    loadChildren: () => import('./features/admin/admin.routes'),
  },

  // Legacy routes (redirect to app)
  { path: 'marketplace', redirectTo: 'app/marketplace' },
  { path: 'portfolio', redirectTo: 'app/portfolio' },
  { path: 'wallet', redirectTo: 'app/wallet' },

  { path: '**', redirectTo: 'home' },
];
