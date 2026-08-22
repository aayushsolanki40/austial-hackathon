import { Component, EventEmitter, Input, Output, computed, inject, signal } from '@angular/core';

import { I18nService } from '../../core/i18n/i18n.service';
import { TPipe } from '../../core/i18n/t.pipe';
import { buildDisclosureChecklist } from '../../core/issuance/disclosure-checklist.util';
import { DisclosureDocument, DisclosureType, REQUIRED_DISCLOSURE_TYPES } from '../../core/issuance/issuance.models';
import { IssuanceService } from '../../core/issuance/issuance.service';
import { IconComponent } from '../components/icon/icon.component';

type SlotUploadState = 'idle' | 'uploading' | 'error';

/**
 * The disclosure-document completeness checklist (gate: `LAUNCHED` is unreachable unless
 * `disclosures_complete` is true) -- reused by both the issuer's own proposal detail view
 * (`uploadable = true`, drives the presign -> S3 PUT -> confirm flow directly, mirroring
 * `DocumentUploadStepComponent`'s KYC-document pattern) and the compliance officer's review
 * screen (`uploadable = false`, read-only view of the same state). Lives under `shared/`
 * rather than a single feature folder for that reason, while still depending on
 * `core/issuance/` the same way `features/admin/` re-exports other core domain types.
 *
 * `missingDisclosureTypes`/`disclosuresComplete` are passed straight through from the parent's
 * `ProposalDetail` (`missing_disclosure_types`/`disclosures_complete`) -- this component never
 * recomputes completeness itself, only renders it (see `buildDisclosureChecklist`).
 *
 * Deliberately keeps its own upload-in-progress state internal (per slot) and just re-emits
 * `uploaded` for the parent to refetch the owning proposal -- refetching is also how the
 * checklist picks up the server's freshly recomputed `missing_disclosure_types` after an
 * upload, rather than this component guessing at the new state itself.
 */
@Component({
  selector: 'app-disclosure-checklist',
  standalone: true,
  imports: [IconComponent, TPipe],
  templateUrl: './disclosure-checklist.component.html',
  styleUrl: './disclosure-checklist.component.scss',
})
export class DisclosureChecklistComponent {
  private readonly issuance = inject(IssuanceService);
  private readonly i18n = inject(I18nService);

  @Input({ required: true }) proposalId!: number;
  @Input() set disclosures(value: DisclosureDocument[]) {
    this.disclosuresSignal.set(value ?? []);
  }
  /** `ProposalDetail.missing_disclosure_types`, server-computed. */
  @Input() set missingDisclosureTypes(value: string[]) {
    this.missingTypesSignal.set(value ?? []);
  }
  /** `ProposalDetail.disclosures_complete`, server-computed -- rendered directly rather than
   * derived from `missingDisclosureTypes.length === 0` so the displayed state always matches
   * exactly what the backend gate saw, even across a stale re-render. */
  @Input() disclosuresComplete = false;
  /** Whether this instance shows upload controls (issuer's own DRAFT/under-review proposal)
   * or renders read-only (compliance review screen, or a proposal past the point disclosures
   * can still change). */
  @Input() uploadable = false;

  /** Fired after a successful upload+confirm so the parent can refetch the owning proposal
   * and pass the fresh `disclosures`/`missingDisclosureTypes` back down. */
  @Output() readonly uploaded = new EventEmitter<void>();

  private readonly disclosuresSignal = signal<DisclosureDocument[]>([]);
  private readonly missingTypesSignal = signal<string[]>([]);
  private readonly slotStateSignal = signal<Record<string, SlotUploadState>>({});

  readonly checklist = computed(() => buildDisclosureChecklist(this.disclosuresSignal(), this.missingTypesSignal()));
  readonly completeCount = computed(() => REQUIRED_DISCLOSURE_TYPES.length - this.missingTypesSignal().length);
  readonly totalCount = REQUIRED_DISCLOSURE_TYPES.length;

  slotState(type: DisclosureType): SlotUploadState {
    return this.slotStateSignal()[type] ?? 'idle';
  }

  async onFileSelected(type: DisclosureType, event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }

    this.setSlotState(type, 'uploading');
    try {
      const contentType = file.type || 'application/octet-stream';
      const presigned = await this.issuance.requestDisclosureUpload(this.proposalId, { disclosure_type: type, content_type: contentType });
      await this.issuance.uploadToPresignedUrl(presigned.upload_url, file, contentType);
      await this.issuance.addDisclosure(this.proposalId, { disclosure_type: type, object_key: presigned.object_key });
      this.setSlotState(type, 'idle');
      this.uploaded.emit();
    } catch {
      this.setSlotState(type, 'error');
    } finally {
      // Allow re-selecting the same file (e.g. retry after an error, or a superseding
      // re-upload of an already-uploaded type) by resetting the input.
      input.value = '';
    }
  }

  typeLabel(type: DisclosureType): string {
    return this.i18n.t(`issuance.disclosure_type.${type.toLowerCase()}`);
  }

  private setSlotState(type: DisclosureType, state: SlotUploadState): void {
    this.slotStateSignal.update((current) => ({ ...current, [type]: state }));
  }
}
