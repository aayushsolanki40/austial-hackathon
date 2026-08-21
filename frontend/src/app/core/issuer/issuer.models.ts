/**
 * ★ CONTRACT ASSUMPTION -- Phase 3's backend `issuers`/`assets` modules had not landed in
 * `backend/src/modules/` at the time this frontend work was done (only `investors`, `kyc`,
 * `auth`, `admin`, `compliance`, `health` exist -- confirmed by reading the backend tree
 * directly, not guessed). These shapes are the frontend's fixed expectation of that
 * backend, modeled directly on the build plan's Phase 3 description ("Issuer with
 * fit-and-proper verification fields", "Asset with asset_class enum") and mirrored on the
 * sibling `investors`/`kyc` modules' *real*, already-shipped shape/conventions (create-once
 * self-service profile, snake_case fields, bare-array list responses). Cross-check field-
 * for-field against `backend/src/modules/issuers/{issuers_controller.py,issuers_dto.py}`
 * and `backend/src/modules/assets/{assets_controller.py,assets_dto.py}` once they exist,
 * and update this file to match if they differ.
 */

/** Mirrors `InvestorProfile.kyc_status`'s "coarse pass/fail flag, not a full state
 * machine" shape (see `core/kyc/kyc.models.ts`) -- an issuer's "fit-and-proper"
 * verification, decided by compliance/admin review of the self-registered profile. There
 * is deliberately no dedicated `IssuerReviewSubmission` sub-resource assumed here (unlike
 * `KycSubmission`) since the build plan doesn't describe one for issuers; if the real
 * backend does add a distinct review workflow, this type and `IssuerService` need updating. */
export type IssuerVerificationStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

/** `GET/POST /issuers/profile` resource shape (assumed `@Roles("ISSUER")`-gated, mirroring
 * `InvestorProfile`). Profile is assumed create-once like `InvestorProfile` -- no `PATCH`. */
export interface IssuerProfile {
  id: number;
  legal_name: string;
  registration_number: string;
  jurisdiction: string;
  contact_email: string;
  verification_status: IssuerVerificationStatus;
  created_at: string;
  updated_at: string;
}

/** `POST /issuers/profile` request body. */
export interface CreateIssuerProfileRequest {
  legal_name: string;
  registration_number: string;
  jurisdiction: string;
  contact_email: string;
}

/** `Asset.asset_class` enum -- verbatim from the build plan's Phase 3 section, the
 * competitive differentiator vs. securities-only rivals. */
export type AssetClass = 'SECURITY' | 'REAL_ESTATE' | 'COMMODITY' | 'INFRASTRUCTURE' | 'IP';

/**
 * `Asset` resource shape. `class_attributes` is assumed to be a flexible JSON blob column
 * (rather than one dedicated column per asset-class-specific field) since the build plan
 * explicitly calls out five very differently-shaped classes (a security's ISIN vs. a real
 * estate asset's location have nothing in common) -- a JSON blob is the assumption least
 * likely to require a frontend rewrite if the real backend picks a narrower/wider set of
 * per-class fields than `ASSET_CLASS_FIELDS` (see `asset-class-fields.ts`) guesses, since
 * only that one config object -- not the request/response shape -- would need to change.
 * If the real backend instead models these as structured per-class columns or a
 * discriminated-union DTO, update this interface and `ASSET_CLASS_FIELDS` together.
 */
export interface Asset {
  id: number;
  issuer_id: number;
  custodian_id: number;
  name: string;
  asset_class: AssetClass;
  description: string;
  valuation_amount: number;
  valuation_currency: string;
  class_attributes: Record<string, string>;
  created_at: string;
  updated_at: string;
}

/** `POST /assets` request body. */
export interface CreateAssetRequest {
  custodian_id: number;
  name: string;
  asset_class: AssetClass;
  description: string;
  valuation_amount: number;
  valuation_currency: string;
  class_attributes: Record<string, string>;
}
