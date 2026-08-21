import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideNoopAnimations } from '@angular/platform-browser/animations';

import { KycSubmission } from '../../../../../core/kyc/kyc.models';
import { KycService } from '../../../../../core/kyc/kyc.service';
import { RiskDisclosureStepComponent } from './risk-disclosure-step.component';

function draftSubmission(overrides: Partial<KycSubmission> = {}): KycSubmission {
  return {
    id: 42,
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
    ...overrides,
  };
}

describe('RiskDisclosureStepComponent', () => {
  let fixture: ComponentFixture<RiskDisclosureStepComponent>;
  let kycServiceStub: { submission: () => KycSubmission | null; submitConsent: jasmine.Spy; submit: jasmine.Spy };

  async function configure(submission: KycSubmission | null): Promise<void> {
    kycServiceStub = {
      submission: signal(submission).asReadonly(),
      submitConsent: jasmine.createSpy('submitConsent'),
      submit: jasmine.createSpy('submit'),
    };

    await TestBed.configureTestingModule({
      imports: [RiskDisclosureStepComponent],
      providers: [provideNoopAnimations(), { provide: KycService, useValue: kycServiceStub }],
    }).compileComponents();

    fixture = TestBed.createComponent(RiskDisclosureStepComponent);
    fixture.detectChanges();
  }

  it('does not submit until the disclosure is acknowledged', async () => {
    await configure(draftSubmission());
    await fixture.componentInstance.submit();
    expect(kycServiceStub.submitConsent).not.toHaveBeenCalled();
    expect(kycServiceStub.submit).not.toHaveBeenCalled();
  });

  it('records the signed consent and finalizes the submission once acknowledged', async () => {
    await configure(draftSubmission());
    kycServiceStub.submitConsent.and.resolveTo({
      id: 1,
      submission_id: 42,
      disclosure_version: fixture.componentInstance.disclosureVersion,
      acknowledged_at: '2026-01-01T00:00:00Z',
    });
    kycServiceStub.submit.and.resolveTo(draftSubmission({ status: 'MANUAL_REVIEW' }));
    const completedSpy = jasmine.createSpy('completed');
    fixture.componentInstance.completed.subscribe(completedSpy);

    fixture.componentInstance.acknowledged.set(true);
    await fixture.componentInstance.submit();

    expect(kycServiceStub.submitConsent).toHaveBeenCalledWith(42, fixture.componentInstance.disclosureVersion);
    expect(kycServiceStub.submit).toHaveBeenCalledWith(42);
    expect(completedSpy).toHaveBeenCalled();
  });

  it('skips re-recording consent when resuming a submission that already has it, but still submits', async () => {
    const consent = { id: 1, submission_id: 42, disclosure_version: 'v1', acknowledged_at: '2026-01-01T00:00:00Z' };
    await configure(draftSubmission({ consent }));
    kycServiceStub.submit.and.resolveTo(draftSubmission({ consent, status: 'MANUAL_REVIEW' }));
    const completedSpy = jasmine.createSpy('completed');
    fixture.componentInstance.completed.subscribe(completedSpy);

    expect(fixture.componentInstance.acknowledged()).toBeTrue();

    await fixture.componentInstance.submit();

    expect(kycServiceStub.submitConsent).not.toHaveBeenCalled();
    expect(kycServiceStub.submit).toHaveBeenCalledWith(42);
    expect(completedSpy).toHaveBeenCalled();
  });

  it('surfaces an error and does not emit completed when the consent call fails', async () => {
    await configure(draftSubmission());
    kycServiceStub.submitConsent.and.rejectWith(new Error('network'));
    const completedSpy = jasmine.createSpy('completed');
    fixture.componentInstance.completed.subscribe(completedSpy);

    fixture.componentInstance.acknowledged.set(true);
    await fixture.componentInstance.submit();

    expect(completedSpy).not.toHaveBeenCalled();
    expect(fixture.componentInstance.errorMessage()).toBeTruthy();
  });
});
