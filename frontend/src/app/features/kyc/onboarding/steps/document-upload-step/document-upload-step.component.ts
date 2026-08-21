import { Component, EventEmitter, Output, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { TPipe } from '../../../../../core/i18n/t.pipe';
import { KycDocumentType } from '../../../../../core/kyc/kyc.models';
import { KycService } from '../../../../../core/kyc/kyc.service';

type UploadStatus = 'idle' | 'uploading' | 'uploaded' | 'error';

interface DocumentUploadState {
  status: UploadStatus;
  fileName: string | null;
}

interface DocumentSlot {
  type: KycDocumentType;
  labelKey: string;
}

/** The submission only requires at least one document to be submittable (see
 * `KycService.submit()`'s `kyc.error.no_documents` gate), but the wizard collects one
 * identity document and one proof of address -- both real values from
 * `KYC_DOCUMENT_TYPES` (`kyc_document.py`). The selfie (also a `KycDocument`, type
 * `SELFIE`) is uploaded separately by the liveness step, through the same flow. */
const DOCUMENT_SLOTS: DocumentSlot[] = [
  { type: 'PASSPORT', labelKey: 'kyc.documents.passport_label' },
  { type: 'PROOF_OF_ADDRESS', labelKey: 'kyc.documents.proof_of_address_label' },
];

/**
 * Onboarding wizard step 2: for each required document, picks a file, requests a
 * presigned S3 PUT URL for the current `KycSubmission`, uploads the file directly to S3,
 * then confirms the upload with the backend. See `KycService` for the three-call flow
 * (`requestDocumentUpload` -> `uploadToPresignedUrl` -> `confirmDocumentUpload`).
 */
@Component({
  selector: 'app-kyc-document-upload-step',
  standalone: true,
  imports: [MatButtonModule, MatIconModule, MatProgressBarModule, TPipe],
  templateUrl: './document-upload-step.component.html',
  styleUrl: './document-upload-step.component.scss',
})
export class DocumentUploadStepComponent {
  private readonly kyc = inject(KycService);

  @Output() readonly completed = new EventEmitter<void>();

  readonly slots = DOCUMENT_SLOTS;

  private readonly uploadsSignal = signal<Record<string, DocumentUploadState>>(
    Object.fromEntries(DOCUMENT_SLOTS.map((slot) => [slot.type, { status: 'idle', fileName: null }]))
  );
  readonly uploads = this.uploadsSignal.asReadonly();

  readonly allUploaded = computed(() =>
    this.slots.every((slot) => this.uploadsSignal()[slot.type]?.status === 'uploaded')
  );

  constructor() {
    // Resuming a DRAFT submission that already has some documents uploaded -- reflect
    // that server-recorded state instead of showing every slot as freshly empty.
    const submission = this.kyc.submission();
    if (submission) {
      for (const document of submission.documents) {
        if (document.document_type in this.uploadsSignal()) {
          this.setState(document.document_type, { status: 'uploaded', fileName: document.object_key });
        }
      }
    }
  }

  stateFor(type: KycDocumentType): DocumentUploadState {
    return this.uploadsSignal()[type] ?? { status: 'idle', fileName: null };
  }

  async onFileSelected(type: KycDocumentType, event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }

    const submissionId = this.kyc.submission()?.id;
    if (submissionId == null) {
      this.setState(type, { status: 'error', fileName: file.name });
      input.value = '';
      return;
    }

    this.setState(type, { status: 'uploading', fileName: file.name });

    try {
      const contentType = file.type || 'application/octet-stream';
      const presigned = await this.kyc.requestDocumentUpload(submissionId, { document_type: type, content_type: contentType });
      await this.kyc.uploadToPresignedUrl(presigned.upload_url, file, contentType);
      await this.kyc.confirmDocumentUpload(submissionId, { document_type: type, object_key: presigned.object_key });
      this.setState(type, { status: 'uploaded', fileName: file.name });
    } catch {
      this.setState(type, { status: 'error', fileName: file.name });
    } finally {
      // Allow re-selecting the same file (e.g. retry after an error) by resetting the input.
      input.value = '';
    }
  }

  continue(): void {
    if (this.allUploaded()) {
      this.completed.emit();
    }
  }

  private setState(type: KycDocumentType, state: DocumentUploadState): void {
    this.uploadsSignal.update((current) => ({ ...current, [type]: state }));
  }
}
