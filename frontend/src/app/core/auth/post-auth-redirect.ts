import { UserRole } from './auth.models';

/**
 * Where to send a user immediately after register/login, based on their
 * *actual* decoded-JWT role rather than a hardcoded path -- each destination
 * is itself role-gated by `roleGuard` (and, for `/app`, `kycVerifiedGuard`
 * too) in `app.routes.ts`, so this only controls the default landing spot,
 * not enforcement.
 *
 * `justRegistered`: a brand new `INVESTOR` account has no KYC profile yet, so
 * send it straight to `/onboarding` rather than `/app` (which would just
 * bounce back to `/onboarding` via `kycVerifiedGuard` anyway, one redirect
 * later). An existing `INVESTOR` logging back in goes to `/app` directly;
 * `kycVerifiedGuard` still catches the case where they never finished
 * onboarding.
 */
export function postAuthRedirectUrl(role: UserRole | null, options: { justRegistered?: boolean } = {}): string {
  switch (role) {
    case 'INVESTOR':
      return options.justRegistered ? '/onboarding' : '/app';
    case 'ISSUER':
      return '/issuer';
    case 'COMPLIANCE_OFFICER':
    case 'ADMIN':
      return '/admin';
    default:
      return '/home';
  }
}
