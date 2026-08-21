import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideNoopAnimations } from '@angular/platform-browser/animations';

import { InvestorProfile } from '../../../../../core/kyc/kyc.models';
import { KycService } from '../../../../../core/kyc/kyc.service';
import { ProfileStepComponent } from './profile-step.component';

function profile(): InvestorProfile {
  return {
    id: 1,
    investor_type: 'INDIVIDUAL',
    jurisdiction: 'IN',
    risk_profile: 'MODERATE',
    kyc_status: 'PENDING',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
}

describe('ProfileStepComponent', () => {
  let fixture: ComponentFixture<ProfileStepComponent>;
  let kycServiceStub: { profile: () => InvestorProfile | null; createProfile: jasmine.Spy; createSubmission: jasmine.Spy };

  function configure(initialProfile: InvestorProfile | null): void {
    kycServiceStub = {
      profile: signal(initialProfile).asReadonly(),
      createProfile: jasmine.createSpy('createProfile'),
      createSubmission: jasmine.createSpy('createSubmission'),
    };
  }

  async function createFixture(): Promise<void> {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ProfileStepComponent],
      providers: [provideNoopAnimations(), { provide: KycService, useValue: kycServiceStub }],
    }).compileComponents();

    fixture = TestBed.createComponent(ProfileStepComponent);
    fixture.detectChanges();
  }

  beforeEach(async () => {
    configure(null);
    await createFixture();
  });

  it('is invalid until all fields are filled in', () => {
    expect(fixture.componentInstance.form.invalid).toBeTrue();
  });

  it('does not submit while the form is invalid', async () => {
    await fixture.componentInstance.submit();
    expect(kycServiceStub.createProfile).not.toHaveBeenCalled();
    expect(kycServiceStub.createSubmission).not.toHaveBeenCalled();
  });

  it('creates the profile and the submission, then emits completed, when there is no profile yet', async () => {
    kycServiceStub.createProfile.and.resolveTo(profile());
    kycServiceStub.createSubmission.and.resolveTo({
      id: 1,
      investor_id: 1,
      status: 'DRAFT',
      legal_name: 'Jane Doe',
      date_of_birth: '1990-01-01',
      nationality: 'IN',
      submitted_at: null,
      screening_result: null,
      reviewed_by_user_id: null,
      review_notes: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      documents: [],
      consent: null,
    });
    const completedSpy = jasmine.createSpy('completed');
    fixture.componentInstance.completed.subscribe(completedSpy);

    fixture.componentInstance.form.setValue({
      investor_type: 'INDIVIDUAL',
      jurisdiction: 'IN',
      risk_profile: 'MODERATE',
      legal_name: 'Jane Doe',
      date_of_birth: '1990-01-01',
      nationality: 'IN',
    });

    await fixture.componentInstance.submit();

    expect(kycServiceStub.createProfile).toHaveBeenCalledWith({
      investor_type: 'INDIVIDUAL',
      jurisdiction: 'IN',
      risk_profile: 'MODERATE',
    });
    expect(kycServiceStub.createSubmission).toHaveBeenCalledWith({
      legal_name: 'Jane Doe',
      date_of_birth: '1990-01-01',
      nationality: 'IN',
    });
    expect(completedSpy).toHaveBeenCalled();
  });

  describe('when a profile already exists', () => {
    beforeEach(async () => {
      configure(profile());
      await createFixture();
    });

    it('disables the profile classification fields and pre-fills them', () => {
      expect(fixture.componentInstance.form.controls.investor_type.disabled).toBeTrue();
      expect(fixture.componentInstance.form.controls.investor_type.value).toBe('INDIVIDUAL');
    });

    it('skips creating the profile again and only creates the submission', async () => {
      kycServiceStub.createSubmission.and.resolveTo({
        id: 1,
        investor_id: 1,
        status: 'DRAFT',
        legal_name: 'Jane Doe',
        date_of_birth: '1990-01-01',
        nationality: 'IN',
        submitted_at: null,
        screening_result: null,
        reviewed_by_user_id: null,
        review_notes: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        documents: [],
        consent: null,
      });
      const completedSpy = jasmine.createSpy('completed');
      fixture.componentInstance.completed.subscribe(completedSpy);

      fixture.componentInstance.form.patchValue({
        legal_name: 'Jane Doe',
        date_of_birth: '1990-01-01',
        nationality: 'IN',
      });

      await fixture.componentInstance.submit();

      expect(kycServiceStub.createProfile).not.toHaveBeenCalled();
      expect(kycServiceStub.createSubmission).toHaveBeenCalledWith({
        legal_name: 'Jane Doe',
        date_of_birth: '1990-01-01',
        nationality: 'IN',
      });
      expect(completedSpy).toHaveBeenCalled();
    });
  });
});
