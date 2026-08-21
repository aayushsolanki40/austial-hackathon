import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiService } from '../api/api.service';
import {
  ConfirmDocumentUploadRequest,
  CreateInvestorProfileRequest,
  CreateKycSubmissionRequest,
  CreateWalletMappingRequest,
  DocumentUploadUrlRequest,
  DocumentUploadUrlResponse,
  InvestorKycStatus,
  InvestorProfile,
  KycDocument,
  KycSubmission,
  RiskDisclosureConsent,
  WalletMapping,
} from './kyc.models';

/** `InvestorProfile.kyc_status` values that mean "not yet decided, don't block the user
 * with an error -- but don't let them into the gated app shell either." Deliberately a
 * denylist (only `VERIFIED` passes `kycVerifiedGuard`) rather than an allowlist of
 * "in review" statuses, so an unexpected/new status from the backend fails closed instead
 * of open. */
const TERMINAL_STATUSES: InvestorKycStatus[] = ['VERIFIED', 'REJECTED'];

/**
 * Signal-based KYC/investor-profile state + calls to the backend's real `/investors/*`
 * and `/kyc/*` endpoints (`InvestorsController`/`KycController`). Mirrors `AuthService`'s
 * pattern: signals for local state, `ApiService` for HTTP, consumed by both the
 * onboarding wizard and `kycVerifiedGuard`.
 *
 * Two separate pieces of state are tracked deliberately, matching the backend's own split:
 * `profile` (the coarse `InvestorProfile`, whose `kyc_status` is only
 * `PENDING | VERIFIED | REJECTED` and is what `kycVerifiedGuard` gates on) and `submission`
 * (the current/latest `KycSubmission`, which carries the full `DRAFT -> ... -> VERIFIED |
 * REJECTED` state machine, its documents, and its risk-disclosure consent record). The
 * onboarding wizard needs both: the profile to know if it should even be here, the
 * submission to know which of its own sub-steps are already done.
 */
@Injectable({ providedIn: 'root' })
export class KycService {
  private readonly api = inject(ApiService);
  private readonly http = inject(HttpClient);

  private readonly profileSignal = signal<InvestorProfile | null>(null);
  private readonly submissionSignal = signal<KycSubmission | null>(null);
  private readonly loadingSignal = signal(false);

  readonly profile = this.profileSignal.asReadonly();
  readonly submission = this.submissionSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();

  readonly kycStatus = computed<InvestorKycStatus | null>(() => this.profileSignal()?.kyc_status ?? null);
  readonly isVerified = computed(() => this.kycStatus() === 'VERIFIED');
  readonly isRejected = computed(() => this.kycStatus() === 'REJECTED');
  readonly isInReview = computed(() => {
    const status = this.kycStatus();
    return status !== null && !TERMINAL_STATUSES.includes(status);
  });

  /**
   * Fetches the current investor's profile (`GET /investors/profile`). Used by both the
   * onboarding wizard (to resume/reflect status) and `kycVerifiedGuard` (to decide
   * whether to let a navigation through). Deliberately swallows HTTP errors -- a 404
   * ("no profile yet, investor hasn't started onboarding") and any other failure are
   * both treated as "not verified" here, since the guard's only job is a pass/fail
   * decision, not surfacing this specific error to the caller.
   */
  async fetchProfile(): Promise<InvestorProfile | null> {
    this.loadingSignal.set(true);
    try {
      const profile = await firstValueFrom(this.api.get<InvestorProfile>('/investors/profile'));
      this.profileSignal.set(profile);
      return profile;
    } catch {
      this.profileSignal.set(null);
      return null;
    } finally {
      this.loadingSignal.set(false);
    }
  }

  /** `POST /investors/profile` -- create-once. Calling this when a profile already
   * exists 409s server-side; callers should check `profile()` first (the onboarding
   * wizard's profile step does exactly that). */
  async createProfile(request: CreateInvestorProfileRequest): Promise<InvestorProfile> {
    const profile = await firstValueFrom(this.api.post<InvestorProfile>('/investors/profile', request));
    this.profileSignal.set(profile);
    return profile;
  }

  async addWalletMapping(request: CreateWalletMappingRequest): Promise<WalletMapping> {
    return firstValueFrom(this.api.post<WalletMapping>('/investors/wallets', request));
  }

  async listWalletMappings(): Promise<WalletMapping[]> {
    return firstValueFrom(this.api.get<WalletMapping[]>('/investors/wallets'));
  }

  /** `POST /kyc/submissions` -- starts a new `DRAFT` submission. 409s if the investor
   * already has a non-terminal (not `VERIFIED`/`REJECTED`) submission. */
  async createSubmission(request: CreateKycSubmissionRequest): Promise<KycSubmission> {
    const submission = await firstValueFrom(this.api.post<KycSubmission>('/kyc/submissions', request));
    this.submissionSignal.set(submission);
    return submission;
  }

  /** `GET /kyc/submissions/:id`. */
  async fetchSubmission(submissionId: number): Promise<KycSubmission> {
    const submission = await firstValueFrom(this.api.get<KycSubmission>(`/kyc/submissions/${submissionId}`));
    this.submissionSignal.set(submission);
    return submission;
  }

  /** `GET /kyc/submissions`, ordered newest-first by the backend -- used on wizard load
   * to resume against whichever submission the investor most recently started, without
   * the caller having to know its id ahead of time. `null` if the investor has never
   * started a submission. */
  async fetchLatestSubmission(): Promise<KycSubmission | null> {
    const submissions = await firstValueFrom(this.api.get<KycSubmission[]>('/kyc/submissions'));
    const latest = submissions[0] ?? null;
    this.submissionSignal.set(latest);
    return latest;
  }

  /** Step 1 of the direct-to-S3 document upload flow: ask the backend for a presigned
   * PUT URL for this submission. Also used for the "liveness" capture -- there is no
   * dedicated liveness endpoint, a captured selfie is just another document with
   * `document_type: 'SELFIE'`. */
  async requestDocumentUpload(submissionId: number, request: DocumentUploadUrlRequest): Promise<DocumentUploadUrlResponse> {
    return firstValueFrom(
      this.api.post<DocumentUploadUrlResponse>(`/kyc/submissions/${submissionId}/documents/upload-url`, request)
    );
  }

  /** Step 2: PUT the file straight to S3 using the presigned URL -- never routed through
   * `ApiService`/the backend origin, so `authInterceptor` correctly leaves it alone. The
   * presigned URL is signed against a specific `Content-Type`, so it must be sent as a
   * header on this direct `PUT` (see `ObjectStorageService.generate_upload_url`). */
  async uploadToPresignedUrl(uploadUrl: string, body: Blob, contentType: string): Promise<void> {
    await firstValueFrom(this.http.put(uploadUrl, body, { headers: { 'Content-Type': contentType } }));
  }

  /** Step 3: tell the backend the direct upload for `object_key` finished. */
  async confirmDocumentUpload(submissionId: number, request: ConfirmDocumentUploadRequest): Promise<KycDocument> {
    return firstValueFrom(this.api.post<KycDocument>(`/kyc/submissions/${submissionId}/documents`, request));
  }

  /** `POST /kyc/submissions/:id/consent` -- persists the signed risk-disclosure consent
   * record (timestamped, versioned). Only allowed while the submission is `DRAFT`;
   * calling it twice for the same submission 409s (the disclosure step checks
   * `submission()?.consent` before calling this again on resume). */
  async submitConsent(submissionId: number, disclosureVersion: string): Promise<RiskDisclosureConsent> {
    return firstValueFrom(
      this.api.post<RiskDisclosureConsent>(`/kyc/submissions/${submissionId}/consent`, {
        disclosure_version: disclosureVersion,
      })
    );
  }

  /** `POST /kyc/submissions/:id/submit` -- `DRAFT -> SUBMITTED -> AUTO_SCREENING ->
   * MANUAL_REVIEW`. Gated server-side on at least one document and a recorded consent
   * (422 `kyc.error.consent_required` otherwise); the wizard's step ordering keeps that
   * from actually happening in practice. Also refetches the investor profile since
   * screening (mocked, synchronous) can in principle complete fast enough to matter. */
  async submit(submissionId: number): Promise<KycSubmission> {
    const submission = await firstValueFrom(this.api.post<KycSubmission>(`/kyc/submissions/${submissionId}/submit`));
    this.submissionSignal.set(submission);
    await this.fetchProfile();
    return submission;
  }
}
