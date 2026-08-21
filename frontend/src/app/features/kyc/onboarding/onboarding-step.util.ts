import { InvestorProfile, KycSubmission, KycSubmissionStatus } from '../../../core/kyc/kyc.models';

/** Index of each `mat-step` in the onboarding wizard's `mat-stepper`. */
export const ONBOARDING_STEP_INDEX = {
  PROFILE: 0,
  DOCUMENTS: 1,
  LIVENESS: 2,
  DISCLOSURE: 3,
  STATUS: 4,
} as const;

/** `KycSubmission.status` values that mean "the investor already finished the profile ->
 * documents -> liveness -> disclosure sequence and is waiting on a decision" -- landing
 * them back on step 0 would be a confusing regression, so these all resume at the status
 * step. */
const IN_REVIEW_STATUSES: KycSubmissionStatus[] = ['SUBMITTED', 'AUTO_SCREENING', 'MANUAL_REVIEW'];

/**
 * Decides which stepper step an investor should land on when the onboarding wizard
 * loads, given their current profile and current/latest `KycSubmission` (either `null` if
 * they don't have one yet). Kept as a pure function, independent of `MatStepper`, so this
 * resume-to-the-right-step decision is unit testable without rendering the component tree.
 *
 * The profile (`investor_type`/`jurisdiction`/`risk_profile`) and the submission's
 * identity fields (`legal_name`/`date_of_birth`/`nationality`) are both collected on the
 * wizard's first step, so "no profile yet" and "no submission yet" are treated the same --
 * both mean "start from the beginning."
 *
 * Within a `DRAFT` submission, resumes at the first sub-step that isn't done yet, using
 * the submission's own `documents`/`consent` (server-recorded state, not client-only
 * flags) rather than re-deriving it:
 * - no non-selfie document yet -> documents step.
 * - has an ID document but no `SELFIE` document -> liveness (selfie-as-document) step.
 * - has both but no recorded consent -> disclosure step (which also triggers the final
 *   `submit` call once consent is in place).
 *
 * `VERIFIED`/`REJECTED` (terminal) or any in-review status -> the wizard's own work is
 * already done; show the status step so the investor sees where they stand instead of
 * re-walking a completed wizard.
 */
export function resolveInitialStep(profile: InvestorProfile | null, submission: KycSubmission | null): number {
  if (!profile || !submission) {
    return ONBOARDING_STEP_INDEX.PROFILE;
  }

  if (submission.status === 'VERIFIED' || submission.status === 'REJECTED') {
    return ONBOARDING_STEP_INDEX.STATUS;
  }

  if (IN_REVIEW_STATUSES.includes(submission.status)) {
    return ONBOARDING_STEP_INDEX.STATUS;
  }

  // submission.status === 'DRAFT' -- resume at the first incomplete sub-step.
  const hasIdDocument = submission.documents.some((doc) => doc.document_type !== 'SELFIE');
  if (!hasIdDocument) {
    return ONBOARDING_STEP_INDEX.DOCUMENTS;
  }

  const hasSelfie = submission.documents.some((doc) => doc.document_type === 'SELFIE');
  if (!hasSelfie) {
    return ONBOARDING_STEP_INDEX.LIVENESS;
  }

  // Whether or not consent is already recorded, the disclosure step is what's left to do --
  // it either still needs to record consent, or just needs to fire the final `submit` call.
  return ONBOARDING_STEP_INDEX.DISCLOSURE;
}
