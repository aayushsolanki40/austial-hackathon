import { TestBed } from '@angular/core/testing';
import { Router, UrlTree, provideRouter } from '@angular/router';

import { InvestorProfile } from '../kyc/kyc.models';
import { KycService } from '../kyc/kyc.service';
import { kycVerifiedGuard } from './kyc-verified.guard';

function profile(kyc_status: InvestorProfile['kyc_status']): InvestorProfile {
  return {
    id: 1,
    investor_type: 'INDIVIDUAL',
    jurisdiction: 'IN',
    risk_profile: 'MODERATE',
    kyc_status,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
}

describe('kycVerifiedGuard', () => {
  let kycServiceStub: { fetchProfile: () => Promise<InvestorProfile | null> };
  let router: Router;

  beforeEach(() => {
    kycServiceStub = { fetchProfile: () => Promise.resolve(null) };
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: KycService, useValue: kycServiceStub }],
    });
    router = TestBed.inject(Router);
  });

  it('allows navigation when kyc_status is VERIFIED', async () => {
    kycServiceStub.fetchProfile = () => Promise.resolve(profile('VERIFIED'));
    const result = await TestBed.runInInjectionContext(() => kycVerifiedGuard({} as never, {} as never));
    expect(result).toBeTrue();
  });

  it('redirects to /onboarding when there is no profile yet', async () => {
    kycServiceStub.fetchProfile = () => Promise.resolve(null);
    const result = (await TestBed.runInInjectionContext(() => kycVerifiedGuard({} as never, {} as never))) as UrlTree;
    expect(result instanceof UrlTree).toBeTrue();
    expect(router.serializeUrl(result)).toBe('/onboarding');
  });

  it('redirects to /onboarding when kyc_status is PENDING/in review', async () => {
    kycServiceStub.fetchProfile = () => Promise.resolve(profile('PENDING'));
    const result = (await TestBed.runInInjectionContext(() => kycVerifiedGuard({} as never, {} as never))) as UrlTree;
    expect(result instanceof UrlTree).toBeTrue();
    expect(router.serializeUrl(result)).toBe('/onboarding');
  });

  it('redirects to /onboarding when kyc_status is REJECTED', async () => {
    kycServiceStub.fetchProfile = () => Promise.resolve(profile('REJECTED'));
    const result = (await TestBed.runInInjectionContext(() => kycVerifiedGuard({} as never, {} as never))) as UrlTree;
    expect(result instanceof UrlTree).toBeTrue();
    expect(router.serializeUrl(result)).toBe('/onboarding');
  });
});
