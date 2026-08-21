import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { KycService } from '../kyc/kyc.service';

/**
 * Real implementation of the build plan's `kycVerifiedGuard` (Section 3
 * route map: `{ path: '', canActivate: [authGuard, kycVerifiedGuard], ... }`).
 * Replaces the Phase-1 permissive pass-through now that Phase 2's investor
 * profile/`kyc_status` exists to check against.
 *
 * Always fetches a fresh profile (rather than trusting a possibly-stale
 * cached `KycService.profile()` signal) since KYC status can change between
 * page loads via async backend screening -- this route is exactly the one
 * place staleness would let an unverified investor slip through. Any
 * non-`VERIFIED` status (including "no profile yet") redirects to
 * `/onboarding`, per the build plan's required flow: login -> KYC status
 * check -> (onboarding if incomplete) -> dashboard.
 */
export const kycVerifiedGuard: CanActivateFn = async () => {
  const kyc = inject(KycService);
  const router = inject(Router);

  const profile = await kyc.fetchProfile();
  if (profile?.kyc_status === 'VERIFIED') {
    return true;
  }

  return router.createUrlTree(['/onboarding']);
};
