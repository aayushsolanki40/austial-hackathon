import { DisclosureDocument, DisclosureType, REQUIRED_DISCLOSURE_TYPES } from './issuance.models';

/** Per-slot status shown in the completeness checklist. Driven entirely by the server-computed
 * `missing_disclosure_types` (see `buildDisclosureChecklist`) -- never re-derived from the raw
 * `disclosures` array, so it's guaranteed to match exactly what `IssuanceService.launch` itself
 * gates on server-side (per `ProposalDetailResponseDto`'s own docstring). */
export type DisclosureSlotStatus = 'missing' | 'uploaded';

export interface DisclosureChecklistItem {
  type: DisclosureType;
  status: DisclosureSlotStatus;
  /** The current document for this type (`is_current: true`), or `null` if `status ===
   * 'missing'`. Which document counts as current is decided server-side (`version`/
   * `is_current` on `DisclosureDocumentResponseDto`), never inferred from `created_at` here. */
  current: DisclosureDocument | null;
  /** Older, superseded documents of this type -- rendered (if at all) as history, never
   * counted toward completeness. */
  history: DisclosureDocument[];
}

/** Builds the fixed six-row checklist for display. `missingDisclosureTypes` and each slot's
 * `status` come straight from `ProposalDetailResponseDto.missing_disclosure_types` -- the
 * completeness gate itself is never reimplemented client-side. `disclosures` is used only to
 * pick which uploaded document to show as "current" per type (via `is_current`) and to list its
 * upload history, which is purely presentational. */
export function buildDisclosureChecklist(disclosures: DisclosureDocument[], missingDisclosureTypes: readonly string[]): DisclosureChecklistItem[] {
  const missing = new Set(missingDisclosureTypes);
  return REQUIRED_DISCLOSURE_TYPES.map((type) => {
    const matches = disclosures.filter((doc) => doc.disclosure_type === type).sort((a, b) => b.created_at.localeCompare(a.created_at));
    const current = matches.find((doc) => doc.is_current) ?? matches[0] ?? null;
    const history = matches.filter((doc) => doc !== current);
    return {
      type,
      status: missing.has(type) ? 'missing' : 'uploaded',
      current,
      history,
    };
  });
}
