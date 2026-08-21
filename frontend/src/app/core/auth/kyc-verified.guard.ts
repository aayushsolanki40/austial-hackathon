import { CanActivateFn } from '@angular/router';

/**
 * Placeholder for the build plan's `kycVerifiedGuard` (Section 3 route
 * map: `{ path: '', canActivate: [authGuard, kycVerifiedGuard], ... }`).
 *
 * Phase 2 backend work (`InvestorProfile.kyc_status`, the KYC review
 * pipeline) hasn't shipped yet, so there is no real KYC status to check
 * against. Wired as a permissive pass-through now purely so the route tree
 * in `app.routes.ts` matches Section 3 exactly and doesn't need a routing
 * change when Phase 2 lands -- only this guard's body needs to change, to
 * read the investor's `kyc_status` (via `AuthService`/`ApiService`) and
 * redirect to `/onboarding` when it isn't `VERIFIED`.
 */
export const kycVerifiedGuard: CanActivateFn = () => true;
