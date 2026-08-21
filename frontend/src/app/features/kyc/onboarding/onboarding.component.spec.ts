import { ComponentFixture, TestBed } from '@angular/core/testing';
import { computed, signal } from '@angular/core';
import { By } from '@angular/platform-browser';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { Router, provideRouter } from '@angular/router';

import { KycService } from '../../../core/kyc/kyc.service';
import { InvestorKycStatus, InvestorProfile, KycSubmission } from '../../../core/kyc/kyc.models';
import { ONBOARDING_STEP_INDEX } from './onboarding-step.util';
import { ProfileStepComponent } from './steps/profile-step/profile-step.component';
import OnboardingComponent from './onboarding.component';

function profile(kyc_status: InvestorKycStatus): InvestorProfile {
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

function inReviewSubmission(): KycSubmission {
  return {
    id: 1,
    investor_id: 1,
    status: 'MANUAL_REVIEW',
    legal_name: 'Jane Doe',
    date_of_birth: '1990-01-01',
    nationality: 'IN',
    submitted_at: '2026-01-01T00:00:00Z',
    screening_result: null,
    reviewed_by_user_id: null,
    review_notes: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    documents: [{ id: 1, document_type: 'PASSPORT', object_key: 'k', ocr_result: null, created_at: '2026-01-01T00:00:00Z' }],
    consent: { id: 1, submission_id: 1, disclosure_version: 'v1', acknowledged_at: '2026-01-01T00:00:00Z' },
  };
}

/** A KycService stand-in built from real signals so every child step component's
 * constructor (which reads `kyc.profile()` etc.) behaves exactly as it would with the
 * real service, without making this a full HTTP-backed integration test. */
function createKycServiceStub(initialProfile: InvestorProfile | null, initialSubmission: KycSubmission | null = null) {
  const profileSignal = signal<InvestorProfile | null>(initialProfile);
  const submissionSignal = signal<KycSubmission | null>(initialSubmission);
  return {
    profile: profileSignal.asReadonly(),
    submission: submissionSignal.asReadonly(),
    kycStatus: computed(() => profileSignal()?.kyc_status ?? null),
    isVerified: computed(() => profileSignal()?.kyc_status === 'VERIFIED'),
    isRejected: computed(() => profileSignal()?.kyc_status === 'REJECTED'),
    isInReview: computed(() => {
      const status = profileSignal()?.kyc_status ?? null;
      return status !== null && status !== 'VERIFIED' && status !== 'REJECTED';
    }),
    fetchProfile: jasmine.createSpy('fetchProfile').and.callFake(async () => profileSignal()),
    createProfile: jasmine.createSpy('createProfile'),
    fetchLatestSubmission: jasmine.createSpy('fetchLatestSubmission').and.callFake(async () => submissionSignal()),
    createSubmission: jasmine.createSpy('createSubmission'),
    requestDocumentUpload: jasmine.createSpy('requestDocumentUpload'),
    uploadToPresignedUrl: jasmine.createSpy('uploadToPresignedUrl'),
    confirmDocumentUpload: jasmine.createSpy('confirmDocumentUpload'),
    submitConsent: jasmine.createSpy('submitConsent'),
    submit: jasmine.createSpy('submit'),
  };
}

describe('OnboardingComponent', () => {
  let fixture: ComponentFixture<OnboardingComponent>;
  let kycServiceStub: ReturnType<typeof createKycServiceStub>;

  async function setup(initialProfile: InvestorProfile | null, initialSubmission: KycSubmission | null = null): Promise<void> {
    kycServiceStub = createKycServiceStub(initialProfile, initialSubmission);
    await TestBed.configureTestingModule({
      imports: [OnboardingComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: KycService, useValue: kycServiceStub },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(OnboardingComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  it('redirects straight to the dashboard when the investor is already VERIFIED', async () => {
    kycServiceStub = createKycServiceStub(profile('VERIFIED'));
    await TestBed.configureTestingModule({
      imports: [OnboardingComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: KycService, useValue: kycServiceStub },
      ],
    }).compileComponents();

    const router = TestBed.inject(Router);
    const navigateSpy = spyOn(router, 'navigateByUrl').and.resolveTo(true);

    fixture = TestBed.createComponent(OnboardingComponent);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(navigateSpy).toHaveBeenCalledWith('/');
  });

  it('starts a fresh investor (no profile) at the profile step with nothing marked complete', async () => {
    await setup(null);

    expect(fixture.componentInstance.selectedIndex()).toBe(ONBOARDING_STEP_INDEX.PROFILE);
    expect(fixture.componentInstance.profileDone()).toBeFalse();
    expect(fixture.componentInstance.documentsDone()).toBeFalse();
  });

  it('resumes an in-review investor directly at the status step with prior steps marked complete', async () => {
    await setup(profile('PENDING'), inReviewSubmission());

    expect(fixture.componentInstance.selectedIndex()).toBe(ONBOARDING_STEP_INDEX.STATUS);
    expect(fixture.componentInstance.profileDone()).toBeTrue();
    expect(fixture.componentInstance.documentsDone()).toBeTrue();
    expect(fixture.componentInstance.livenessDone()).toBeTrue();
    expect(fixture.componentInstance.disclosureDone()).toBeTrue();
  });

  it('advances the stepper and marks the profile step complete when the profile step completes', async () => {
    await setup(null);

    expect(fixture.componentInstance.selectedIndex()).toBe(ONBOARDING_STEP_INDEX.PROFILE);

    const profileStep = fixture.debugElement.query(By.directive(ProfileStepComponent))
      .componentInstance as ProfileStepComponent;
    profileStep.completed.emit();
    fixture.detectChanges();

    expect(fixture.componentInstance.profileDone()).toBeTrue();
    expect(fixture.componentInstance.selectedIndex()).toBe(ONBOARDING_STEP_INDEX.DOCUMENTS);
  });

  it('advances profile -> documents -> liveness -> disclosure -> status in order via each step completed event', async () => {
    await setup(null);

    fixture.componentInstance.onProfileCompleted();
    expect(fixture.componentInstance.selectedIndex()).toBe(ONBOARDING_STEP_INDEX.DOCUMENTS);

    fixture.componentInstance.onDocumentsCompleted();
    expect(fixture.componentInstance.selectedIndex()).toBe(ONBOARDING_STEP_INDEX.LIVENESS);

    fixture.componentInstance.onLivenessCompleted();
    expect(fixture.componentInstance.selectedIndex()).toBe(ONBOARDING_STEP_INDEX.DISCLOSURE);

    fixture.componentInstance.onDisclosureCompleted();
    expect(fixture.componentInstance.selectedIndex()).toBe(ONBOARDING_STEP_INDEX.STATUS);
    expect(fixture.componentInstance.disclosureDone()).toBeTrue();
  });
});
