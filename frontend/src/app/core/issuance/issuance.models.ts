/**
 * Request/response shapes for the Phase 4 `issuance` backend module.
 *
 * Reconciled against the real backend contract --
 * `backend/src/modules/issuance/{issuance_controller.py,issuance_dto.py}` -- field names and
 * endpoint shapes below are copied directly from `issuance_dto.py`, not inferred.
 */

/** The full state machine, mirrored from `issuance_service.py`'s transitions. `REJECTED` is a
 * terminal branch reachable only from `DOCUMENTATION_REVIEW` and `IFSCA_FILED` (enforced
 * server-side; the frontend just reflects whatever status comes back). */
export type ProposalStatus =
  | 'DRAFT'
  | 'DOCUMENTATION_REVIEW'
  | 'COMPLIANCE_APPROVED'
  | 'IFSCA_FILED'
  | 'IFSCA_APPROVED'
  | 'LAUNCHED'
  | 'REJECTED';

/** `POST /issuance/proposals` request body -- `CreateProposalDto`. Validated server-side:
 * `subscription_end_at > subscription_start_at`, `min_subscription_units <= total_units`. */
export interface CreateProposalRequest {
  asset_id: number;
  total_units: number;
  unit_price_usd: number;
  min_subscription_units: number;
  subscription_start_at: string;
  subscription_end_at: string;
}

/** `ProposalResponseDto` -- the shape returned by list endpoints (`GET /proposals`,
 * `GET /proposals/mine`). Deliberately does NOT include `disclosures`/
 * `missing_disclosure_types`/`disclosures_complete` -- those only exist on the detail response
 * (`ProposalDetail` below). */
export interface TokenizationProposal {
  id: number;
  asset_id: number;
  issuer_id: number;
  total_units: number;
  unit_price_usd: number;
  min_subscription_units: number;
  subscription_start_at: string;
  subscription_end_at: string;
  status: ProposalStatus;
  ifsca_filing_reference: string | null;
  ifsca_approval_reference: string | null;
  rejection_reason: string | null;
  reviewed_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

/** `ProposalDetailResponseDto` -- returned by create/get-single (`/proposals/:id`,
 * `/proposals/mine/:id`) endpoints. Embeds the server-computed disclosure-completeness
 * checklist verbatim: `missing_disclosure_types` is exactly what `IssuanceService.launch`
 * itself checks, so the frontend must render these fields directly rather than re-deriving
 * completeness from a raw `disclosures` array (see `disclosure-checklist.util.ts`). */
export interface ProposalDetail extends TokenizationProposal {
  disclosures: DisclosureDocument[];
  missing_disclosure_types: string[];
  disclosures_complete: boolean;
}

/** `ProposalListDto` -- envelope for both `GET /proposals` and `GET /proposals/mine`. `items`
 * is always the lighter `TokenizationProposal` (`ProposalResponseDto`), never `ProposalDetail`. */
export interface ProposalListResponse {
  total: number;
  items: TokenizationProposal[];
}

/** `POST /issuance/proposals/:id/reject` request body -- `RejectProposalDto`. */
export interface RejectProposalRequest {
  reason: string;
}

/** `POST /issuance/proposals/:id/file-ifsca` request body -- `FileIfscaDto`. */
export interface FileIfscaRequest {
  filing_reference: string;
}

/** `POST /issuance/proposals/:id/ifsca-approve` request body -- `IfscaApproveDto`. */
export interface IfscaApproveRequest {
  approval_reference: string;
}

/** `POST /issuance/proposals/:id/launch` request body -- `LaunchProposalDto`. `symbol` is
 * required; `contract_address` is optional (recorded later via the smart-contract-deployment
 * action if a DLT execution layer is used). */
export interface LaunchProposalRequest {
  symbol: string;
  contract_address?: string;
}

/** The closed six-type set `DISCLOSURE_TYPES` names verbatim (`disclosure_document.py`). */
export type DisclosureType = 'RISK' | 'FEE' | 'LIQUIDITY' | 'CUSTODY' | 'TAX' | 'PROSPECTUS';

export const REQUIRED_DISCLOSURE_TYPES: readonly DisclosureType[] = ['RISK', 'FEE', 'LIQUIDITY', 'CUSTODY', 'TAX', 'PROSPECTUS'];

/** `POST /issuance/proposals/mine/:id/disclosures/upload-url` request --
 * `DisclosureUploadUrlRequestDto`. */
export interface DisclosureUploadUrlRequest {
  disclosure_type: DisclosureType;
  content_type: string;
}

/** Response to the above -- `DisclosureUploadUrlResponseDto`. */
export interface DisclosureUploadUrlResponse {
  upload_url: string;
  object_key: string;
}

/** `POST /issuance/proposals/mine/:id/disclosures` confirm-step body -- `AddDisclosureDto`. */
export interface AddDisclosureRequest {
  disclosure_type: DisclosureType;
  object_key: string;
}

/** `DisclosureDocumentResponseDto`. Uploading a type that already has a current document adds
 * a new versioned row (`version`/`is_current`) rather than overwriting in place -- the backend
 * tracks which row is current, the frontend never has to infer it from `created_at` alone. */
export interface DisclosureDocument {
  id: number;
  disclosure_type: DisclosureType;
  object_key: string;
  version: number;
  is_current: boolean;
  created_at: string;
}

/** `TokenSeriesResponseDto` -- a standalone resource (its own `GET /token-series/:id`), not
 * embedded on `ProposalDetail`. Created atomically by `launch()`, whose response IS this shape
 * directly (not a `ProposalDetail`) -- see `IssuanceService.launch` in `issuance.service.ts`. */
export interface TokenSeries {
  id: number;
  proposal_id: number;
  symbol: string;
  total_supply: number;
  contract_address: string | null;
  paused: boolean;
  smart_contract_deployment_id: number | null;
  created_at: string;
  updated_at: string;
}

/** `POST /issuance/token-series/:id/smart-contract-deployment` request body --
 * `RecordSmartContractDeploymentDto`. Optional action, not gating `launch()` -- per the build
 * plan, only required "if a DLT execution layer is used". */
export interface RecordSmartContractDeploymentRequest {
  bytecode_hash: string;
  version: string;
  audit_report_ref?: string;
}
