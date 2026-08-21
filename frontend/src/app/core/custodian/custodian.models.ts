/**
 * Request/response shapes for the real Phase 3 `custodians` backend module -- confirmed
 * against `backend/src/modules/custodians/{custodians_controller.py,custodians_dto.py}`.
 * `ifsca_verified` is the field the build plan calls out explicitly: "an asset cannot be
 * tokenized unless its custodian row is IFSCA-verified." `GET /custodians`/`GET
 * /custodians/:id` are readable by both `COMPLIANCE_OFFICER` and `ISSUER` (handler-level
 * `@Roles(...)` override) so an issuer can pick a verified custodian for their asset;
 * create/verify stay `COMPLIANCE_OFFICER`-only.
 */
export interface Custodian {
  id: number;
  name: string;
  ifsca_registration_no: string;
  ifsca_verified: boolean;
  verified_by_user_id: number | null;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
}

/** `POST /custodians` request body (`CreateCustodianDto`), `COMPLIANCE_OFFICER`-only. */
export interface CreateCustodianRequest {
  name: string;
  ifsca_registration_no: string;
}

/** `GET /custodians?skip=&take=` response (`CustodianListDto`). */
export interface CustodianListResponse {
  total: number;
  items: Custodian[];
}
