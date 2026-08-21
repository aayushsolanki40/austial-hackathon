/**
 * Request/response shapes for the real Phase 2 `investors`/`kyc` backend modules --
 * confirmed against `backend/src/modules/investors/{investors_controller.py,investors_dto.py}`
 * and `backend/src/modules/kyc/{kyc_controller.py,kyc_dto.py}`. Field names/types below are a
 * direct mirror of the backend's Pydantic DTOs; keep in sync if those change.
 */

/** `InvestorProfile.kyc_status` -- deliberately a *small* closed set (see
 * `investor_profile.py`'s `KYC_STATUSES`). This is a coarse "can this investor use the
 * gated app shell" flag, flipped only when a `KycSubmission` is approved/rejected --
 * it is NOT the granular submission state machine, see `KycSubmissionStatus` for that. */
export type InvestorKycStatus = 'PENDING' | 'VERIFIED' | 'REJECTED';

export type InvestorType = 'INDIVIDUAL' | 'INSTITUTIONAL';

export type RiskProfile = 'CONSERVATIVE' | 'MODERATE' | 'AGGRESSIVE';

/** `GET/POST /investors/profile` resource shape. Profile is create-once -- there is no
 * `PATCH`/update endpoint in this version of the backend; a second `POST` 409s. */
export interface InvestorProfile {
  id: number;
  investor_type: InvestorType | null;
  jurisdiction: string | null;
  risk_profile: RiskProfile | null;
  kyc_status: InvestorKycStatus;
  created_at: string;
  updated_at: string;
}

/** `POST /investors/profile` request body (`CreateInvestorProfileDto`). */
export interface CreateInvestorProfileRequest {
  investor_type: InvestorType;
  jurisdiction: string;
  risk_profile: RiskProfile;
}

export type WalletChain = 'ETHEREUM' | 'POLYGON' | 'PERMISSIONED_DLT';

export type WalletMappingStatus = 'ACTIVE' | 'REVOKED';

/** `GET /investors/wallets` item / `POST /investors/wallets` response. */
export interface WalletMapping {
  id: number;
  chain: WalletChain;
  address: string;
  label: string | null;
  status: WalletMappingStatus;
  created_at: string;
}

/** `POST /investors/wallets` request body (`CreateWalletMappingDto`). */
export interface CreateWalletMappingRequest {
  chain: WalletChain;
  address: string;
  label?: string | null;
}

/** `KycSubmission.status` -- the full state machine (`ALLOWED_TRANSITIONS` in
 * `kyc_service.py`): `DRAFT -> SUBMITTED -> AUTO_SCREENING -> MANUAL_REVIEW -> VERIFIED |
 * REJECTED`. Lives on the submission, not the investor profile. */
export type KycSubmissionStatus = 'DRAFT' | 'SUBMITTED' | 'AUTO_SCREENING' | 'MANUAL_REVIEW' | 'VERIFIED' | 'REJECTED';

/** `POST /kyc/submissions` request body (`CreateKycSubmissionDto`). `date_of_birth` is an
 * ISO date string (`YYYY-MM-DD`), `nationality` an ISO 3166-1 alpha-2 code. */
export interface CreateKycSubmissionRequest {
  legal_name: string;
  date_of_birth: string;
  nationality: string;
}

/** The closed document-type enum the backend actually validates against
 * (`KYC_DOCUMENT_TYPES` in `kyc_document.py`). There is no dedicated liveness endpoint --
 * a captured selfie is uploaded through this same document flow with `document_type:
 * 'SELFIE'` (see `KycService.requestDocumentUpload`/`confirmDocumentUpload`). */
export type KycDocumentType = 'PASSPORT' | 'NATIONAL_ID' | 'DRIVERS_LICENSE' | 'PROOF_OF_ADDRESS' | 'SELFIE';

/** `POST /kyc/submissions/:id/documents/upload-url` request (`DocumentUploadUrlRequestDto`). */
export interface DocumentUploadUrlRequest {
  document_type: KycDocumentType;
  content_type: string;
}

/** `POST /kyc/submissions/:id/documents/upload-url` response
 * (`DocumentUploadUrlResponseDto`) -- a presigned S3 `PUT` URL the browser uploads
 * directly to, plus the `object_key` to hand back when confirming. */
export interface DocumentUploadUrlResponse {
  upload_url: string;
  object_key: string;
}

/** `POST /kyc/submissions/:id/documents` request (`AddKycDocumentDto`) -- tells the
 * backend the direct-to-S3 upload for `object_key` finished. */
export interface ConfirmDocumentUploadRequest {
  document_type: KycDocumentType;
  object_key: string;
}

/** `KycDocumentResponseDto`. `ocr_result` is `null` until the mock OCR provider (run
 * synchronously as part of `POST /kyc/submissions/:id/submit`) processes it. */
export interface KycDocument {
  id: number;
  document_type: KycDocumentType;
  object_key: string;
  ocr_result: Record<string, unknown> | null;
  created_at: string;
}

/** `POST /kyc/submissions/:id/consent` request (`RecordRiskDisclosureConsentDto`).
 * `disclosure_version` is a stable string constant identifying the risk-disclosure copy
 * shown to the investor -- the backend just stores whatever string is sent. */
export interface RecordRiskDisclosureConsentRequest {
  disclosure_version: string;
}

/** `RiskDisclosureConsentResponseDto`, also embedded as `KycSubmission.consent`. */
export interface RiskDisclosureConsent {
  id: number;
  submission_id: number;
  disclosure_version: string;
  acknowledged_at: string;
}

/** `KycSubmissionResponseDto` -- returned by create/get/list/submit/approve/reject.
 * `consent` is `null` until the investor has acknowledged the risk disclosure for this
 * specific submission; the onboarding wizard uses that (not client-only state) to decide
 * whether the disclosure step still needs action when resuming. */
export interface KycSubmission {
  id: number;
  investor_id: number;
  status: KycSubmissionStatus;
  legal_name: string;
  date_of_birth: string;
  nationality: string;
  submitted_at: string | null;
  screening_result: Record<string, unknown> | null;
  reviewed_by_user_id: number | null;
  review_notes: string | null;
  created_at: string;
  updated_at: string;
  documents: KycDocument[];
  consent: RiskDisclosureConsent | null;
}

/** `GET /kyc/review-queue` response (`KycSubmissionListDto`). */
export interface KycSubmissionListResponse {
  total: number;
  items: KycSubmission[];
}

/** `POST /kyc/submissions/:id/reject` request body (`RejectKycSubmissionDto`). */
export interface RejectKycSubmissionRequest {
  reason: string;
}
