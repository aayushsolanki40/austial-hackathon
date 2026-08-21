/**
 * ★ CONTRACT ASSUMPTION -- see the header of `core/issuer/issuer.models.ts` for the full
 * caveat (Phase 3's `custodians` backend module hadn't landed yet when this was written).
 * `Custodian.ifsca_verified` is the field the build plan calls out explicitly: "an asset
 * cannot be tokenized unless its custodian row is IFSCA-verified." Listing is assumed to
 * be a plain top-level `/custodians` module (not nested under `/admin`), since an ISSUER
 * needs to read this list too (to pick a custodian for `Asset.custodian_id`) and shouldn't
 * need `/admin/*` access to do so -- create/verify are assumed to still be server-side
 * role-gated to `COMPLIANCE_OFFICER`/`ADMIN` even though the route is shared.
 */
export interface Custodian {
  id: number;
  name: string;
  ifsca_registration_no: string;
  jurisdiction: string;
  ifsca_verified: boolean;
  created_at: string;
  updated_at: string;
}

/** `POST /custodians` request body (assumed `COMPLIANCE_OFFICER`/`ADMIN`-gated). */
export interface CreateCustodianRequest {
  name: string;
  ifsca_registration_no: string;
  jurisdiction: string;
}
