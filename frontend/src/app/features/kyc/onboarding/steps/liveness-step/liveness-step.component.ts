import { Component, ElementRef, EventEmitter, OnDestroy, Output, ViewChild, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { I18nService } from '../../../../../core/i18n/i18n.service';
import { TPipe } from '../../../../../core/i18n/t.pipe';
import { KycService } from '../../../../../core/kyc/kyc.service';

const SELFIE_CONTENT_TYPE = 'image/jpeg';

/**
 * Onboarding wizard step 3: real webcam capture flow (`getUserMedia` -> draw the current
 * frame to a `<canvas>` -> submit the JPEG). There is no dedicated liveness/face-match
 * endpoint -- the backend's mocked liveness/face-match provider runs as part of
 * `POST /kyc/submissions/:id/submit`'s auto-screening pipeline, against whichever document
 * has `document_type: 'SELFIE'`. So "submitting" a liveness capture here just means
 * running it through the same presign -> direct-S3-PUT -> confirm document flow as
 * `DocumentUploadStepComponent`, with `document_type: 'SELFIE'`.
 */
@Component({
  selector: 'app-kyc-liveness-step',
  standalone: true,
  imports: [MatButtonModule, MatProgressSpinnerModule, TPipe],
  templateUrl: './liveness-step.component.html',
  styleUrl: './liveness-step.component.scss',
})
export class LivenessStepComponent implements OnDestroy {
  private readonly kyc = inject(KycService);
  private readonly i18n = inject(I18nService);

  @Output() readonly completed = new EventEmitter<void>();

  @ViewChild('video') private readonly videoRef?: ElementRef<HTMLVideoElement>;
  @ViewChild('canvas') private readonly canvasRef?: ElementRef<HTMLCanvasElement>;

  private stream: MediaStream | null = null;

  readonly cameraActive = signal(false);
  readonly capturedImage = signal<string | null>(null);
  readonly submitting = signal(false);
  readonly errorMessage = signal<string | null>(null);

  async startCamera(): Promise<void> {
    this.errorMessage.set(null);

    if (!navigator.mediaDevices?.getUserMedia) {
      this.errorMessage.set(this.i18n.t('kyc.liveness_error.camera_unavailable'));
      return;
    }

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      const video = this.videoRef?.nativeElement;
      if (video) {
        video.srcObject = this.stream;
        await video.play().catch(() => undefined);
      }
      this.cameraActive.set(true);
    } catch {
      this.errorMessage.set(this.i18n.t('kyc.liveness_error.camera_permission_denied'));
    }
  }

  capture(): void {
    const video = this.videoRef?.nativeElement;
    const canvas = this.canvasRef?.nativeElement;
    if (!video || !canvas) {
      return;
    }

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    this.capturedImage.set(canvas.toDataURL(SELFIE_CONTENT_TYPE));
    this.stopCamera();
  }

  async retake(): Promise<void> {
    this.capturedImage.set(null);
    await this.startCamera();
  }

  async submit(): Promise<void> {
    const image = this.capturedImage();
    const submissionId = this.kyc.submission()?.id;
    if (!image || submissionId == null || this.submitting()) {
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set(null);
    try {
      const blob = await this.dataUrlToBlob(image);
      const presigned = await this.kyc.requestDocumentUpload(submissionId, {
        document_type: 'SELFIE',
        content_type: SELFIE_CONTENT_TYPE,
      });
      await this.kyc.uploadToPresignedUrl(presigned.upload_url, blob, SELFIE_CONTENT_TYPE);
      await this.kyc.confirmDocumentUpload(submissionId, { document_type: 'SELFIE', object_key: presigned.object_key });
      this.completed.emit();
    } catch {
      this.errorMessage.set(this.i18n.t('kyc.liveness_error.submit_failed'));
    } finally {
      this.submitting.set(false);
    }
  }

  ngOnDestroy(): void {
    this.stopCamera();
  }

  private stopCamera(): void {
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    this.cameraActive.set(false);
  }

  private async dataUrlToBlob(dataUrl: string): Promise<Blob> {
    const response = await fetch(dataUrl);
    return response.blob();
  }
}
