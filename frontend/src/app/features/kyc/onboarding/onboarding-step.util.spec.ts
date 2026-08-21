import { InvestorProfile, KycDocument, KycSubmission, KycSubmissionStatus } from '../../../core/kyc/kyc.models';
import { ONBOARDING_STEP_INDEX, resolveInitialStep } from './onboarding-step.util';

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

function document(document_type: KycDocument['document_type']): KycDocument {
  return { id: 1, document_type, object_key: 'kyc/1/1/doc', ocr_result: null, created_at: '2026-01-01T00:00:00Z' };
}

function submissionWithStatus(
  status: KycSubmissionStatus,
  overrides: Partial<KycSubmission> = {}
): KycSubmission {
  return {
    id: 1,
    investor_id: 1,
    status,
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

describe('resolveInitialStep', () => {
  it('starts at the profile step when there is no profile yet', () => {
    expect(resolveInitialStep(null, null)).toBe(ONBOARDING_STEP_INDEX.PROFILE);
  });

  it('starts at the profile step when there is a profile but no submission yet', () => {
    expect(resolveInitialStep(profile(), null)).toBe(ONBOARDING_STEP_INDEX.PROFILE);
  });

  it('resumes at the documents step for a DRAFT submission with no documents', () => {
    expect(resolveInitialStep(profile(), submissionWithStatus('DRAFT'))).toBe(ONBOARDING_STEP_INDEX.DOCUMENTS);
  });

  it('resumes at the liveness step for a DRAFT submission with an ID document but no selfie', () => {
    const submission = submissionWithStatus('DRAFT', { documents: [document('PASSPORT')] });
    expect(resolveInitialStep(profile(), submission)).toBe(ONBOARDING_STEP_INDEX.LIVENESS);
  });

  it('resumes at the disclosure step for a DRAFT submission with an ID document and a selfie but no consent', () => {
    const submission = submissionWithStatus('DRAFT', { documents: [document('PASSPORT'), document('SELFIE')] });
    expect(resolveInitialStep(profile(), submission)).toBe(ONBOARDING_STEP_INDEX.DISCLOSURE);
  });

  it('resumes at the disclosure step for a DRAFT submission with documents and consent already recorded', () => {
    const submission = submissionWithStatus('DRAFT', {
      documents: [document('PASSPORT'), document('SELFIE')],
      consent: { id: 1, submission_id: 1, disclosure_version: 'v1', acknowledged_at: '2026-01-01T00:00:00Z' },
    });
    expect(resolveInitialStep(profile(), submission)).toBe(ONBOARDING_STEP_INDEX.DISCLOSURE);
  });

  const inReviewStatuses: KycSubmissionStatus[] = ['SUBMITTED', 'AUTO_SCREENING', 'MANUAL_REVIEW'];
  for (const status of inReviewStatuses) {
    it(`resumes at the status step for in-review status ${status}`, () => {
      expect(resolveInitialStep(profile(), submissionWithStatus(status))).toBe(ONBOARDING_STEP_INDEX.STATUS);
    });
  }

  it('resumes at the status step when VERIFIED', () => {
    expect(resolveInitialStep(profile(), submissionWithStatus('VERIFIED'))).toBe(ONBOARDING_STEP_INDEX.STATUS);
  });

  it('resumes at the status step when REJECTED', () => {
    expect(resolveInitialStep(profile(), submissionWithStatus('REJECTED'))).toBe(ONBOARDING_STEP_INDEX.STATUS);
  });
});
