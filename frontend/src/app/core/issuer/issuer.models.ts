/**
 * Request/response shapes for the real Phase 3 `issuers`/`assets` backend modules --
 * confirmed against `backend/src/modules/issuers/{issuers_controller.py,issuers_dto.py}` and
 * `backend/src/modules/assets/{assets_controller.py,assets_dto.py}`. Field names/types below are
 * a direct mirror of the backend's Pydantic DTOs; keep in sync if those change.
 */

/** `Issuer.verification_status` -- the backend's actual closed set (`IssuerResponseDto`),
 * flipped only by a `COMPLIANCE_OFFICER` calling `POST /issuers/:id/approve` or `.../reject`. */
export type IssuerVerificationStatus = 'PENDING' | 'VERIFIED' | 'REJECTED';

/** `GET/POST /issuers/profile` resource shape (`IssuerResponseDto`, `@Roles("ISSUER")`-gated).
 * Profile is create-once -- there is no `PATCH`/update endpoint; a second `POST` is expected
 * to 409 server-side (mirrors `InvestorProfile`/`IssuerProfile`'s sibling conventions). */
export interface IssuerProfile {
  id: number;
  legal_name: string;
  registration_number: string;
  registration_jurisdiction: string;
  verification_status: IssuerVerificationStatus;
  verified_by_user_id: number | null;
  verified_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

/** `POST /issuers/profile` request body (`CreateIssuerDto`). `registration_jurisdiction` must
 * be a valid ISO 3166-1 alpha-2 code -- the backend validates and normalizes to uppercase. */
export interface CreateIssuerProfileRequest {
  legal_name: string;
  registration_number: string;
  registration_jurisdiction: string;
}

/** `GET /issuers/review-queue?skip=&take=` response (`IssuerListDto`), `@Roles("COMPLIANCE_OFFICER")`. */
export interface IssuerReviewQueueResponse {
  total: number;
  items: IssuerProfile[];
}

/** `POST /issuers/:id/reject` request body (`RejectIssuerDto`). */
export interface RejectIssuerRequest {
  reason: string;
}

/** `Asset.asset_class` enum (`ASSET_CLASSES` in `entities/asset.py`) -- the competitive
 * differentiator vs. securities-only rivals, called out in the build plan's Phase 3 section. */
export type AssetClass = 'SECURITY' | 'REAL_ESTATE' | 'COMMODITY' | 'INFRASTRUCTURE' | 'IP';

/** `Asset` resource shape (`AssetResponseDto`). There is deliberately no `class_attributes`
 * JSON blob and no `valuation_amount`/`valuation_currency` -- the real `Asset` entity is just
 * `name` + `asset_class` + `description`, nothing class-specific stored server-side.
 * `custodian_verified` is a denormalized snapshot of `custodian.ifsca_verified` at attach
 * time; `tokenization_ready` is a computed (`custodian is not None`) DTO-layer field, not a
 * stored column -- see `entities/asset.py`'s docstring. */
export interface Asset {
  id: number;
  issuer_id: number;
  custodian_id: number | null;
  name: string;
  asset_class: AssetClass;
  description: string | null;
  custodian_verified: boolean;
  tokenization_ready: boolean;
  created_at: string;
  updated_at: string;
}

/** `POST /assets` request body (`CreateAssetDto`). No `class_attributes`, no
 * `custodian_id`/valuation fields -- custodian attachment is a separate step, see
 * `AttachCustodianRequest`/`POST /assets/:id/custodian`. */
export interface CreateAssetRequest {
  name: string;
  asset_class: AssetClass;
  description?: string;
}

/** `GET /assets?skip=&take=` response (`AssetListDto`), scoped server-side to the caller's
 * own issuer profile. */
export interface AssetListResponse {
  total: number;
  items: Asset[];
}

/** `POST /assets/:id/custodian` request body (`AttachCustodianDto`). The backend enforces
 * (service + DB composite FK) that `custodian_id` refers to an `ifsca_verified` custodian --
 * 409 otherwise. */
export interface AttachCustodianRequest {
  custodian_id: number;
}
