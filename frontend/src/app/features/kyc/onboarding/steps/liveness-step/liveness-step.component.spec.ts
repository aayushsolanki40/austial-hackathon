import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideNoopAnimations } from '@angular/platform-browser/animations';

import { KycSubmission } from '../../../../../core/kyc/kyc.models';
import { KycService } from '../../../../../core/kyc/kyc.service';
import { LivenessStepComponent } from './liveness-step.component';

function draftSubmission(): KycSubmission {
  return {
    id: 42,
    investor_id: 1,
    status: 'DRAFT',
    legal_name: 'Jane Doe',
    date_of_birth: '1990-01-01',
    nationality: 'IN',
    submitted_at: null,
    screening_result: null,
    reviewed_by_user_id: null,
    review_notes: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    documents: [],
    consent: null,
  };
}

describe('LivenessStepComponent', () => {
  let fixture: ComponentFixture<LivenessStepComponent>;
  let kycServiceStub: {
    submission: () => KycSubmission | null;
    requestDocumentUpload: jasmine.Spy;
    uploadToPresignedUrl: jasmine.Spy;
    confirmDocumentUpload: jasmine.Spy;
  };
  let originalMediaDevices: MediaDevices | undefined;

  beforeEach(async () => {
    kycServiceStub = {
      submission: signal(draftSubmission()).asReadonly(),
      requestDocumentUpload: jasmine.createSpy('requestDocumentUpload'),
      uploadToPresignedUrl: jasmine.createSpy('uploadToPresignedUrl'),
      confirmDocumentUpload: jasmine.createSpy('confirmDocumentUpload'),
    };
    originalMediaDevices = navigator.mediaDevices;

    await TestBed.configureTestingModule({
      imports: [LivenessStepComponent],
      providers: [provideNoopAnimations(), { provide: KycService, useValue: kycServiceStub }],
    }).compileComponents();

    fixture = TestBed.createComponent(LivenessStepComponent);
    fixture.detectChanges();
  });

  afterEach(() => {
    Object.defineProperty(navigator, 'mediaDevices', { value: originalMediaDevices, configurable: true });
  });

  it('shows a camera-unavailable error when getUserMedia is not supported', async () => {
    Object.defineProperty(navigator, 'mediaDevices', { value: undefined, configurable: true });

    await fixture.componentInstance.startCamera();

    expect(fixture.componentInstance.cameraActive()).toBeFalse();
    expect(fixture.componentInstance.errorMessage()).toContain("isn't supported");
  });

  it('shows a permission-denied error when getUserMedia rejects', async () => {
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: jasmine.createSpy('getUserMedia').and.rejectWith(new Error('denied')) },
    });

    await fixture.componentInstance.startCamera();

    expect(fixture.componentInstance.cameraActive()).toBeFalse();
    expect(fixture.componentInstance.errorMessage()).toContain('denied');
  });

  it('does not submit without a captured image', async () => {
    await fixture.componentInstance.submit();
    expect(kycServiceStub.requestDocumentUpload).not.toHaveBeenCalled();
  });

  it('submits the captured frame as a SELFIE document and emits completed on success', async () => {
    kycServiceStub.requestDocumentUpload.and.resolveTo({ upload_url: 'https://s3.example.com/obj', object_key: 'kyc/1/42/selfie/abc' });
    kycServiceStub.uploadToPresignedUrl.and.resolveTo(undefined);
    kycServiceStub.confirmDocumentUpload.and.resolveTo({
      id: 2,
      document_type: 'SELFIE',
      object_key: 'kyc/1/42/selfie/abc',
      ocr_result: null,
      created_at: '2026-01-01T00:00:00Z',
    });
    const completedSpy = jasmine.createSpy('completed');
    fixture.componentInstance.completed.subscribe(completedSpy);
    // 1x1 transparent PNG data URL -- small enough to `fetch()`/`.blob()` synchronously in jsdom/Karma.
    fixture.componentInstance.capturedImage.set(
      'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
    );

    await fixture.componentInstance.submit();

    expect(kycServiceStub.requestDocumentUpload).toHaveBeenCalledWith(42, { document_type: 'SELFIE', content_type: 'image/jpeg' });
    expect(kycServiceStub.uploadToPresignedUrl).toHaveBeenCalledWith('https://s3.example.com/obj', jasmine.any(Blob), 'image/jpeg');
    expect(kycServiceStub.confirmDocumentUpload).toHaveBeenCalledWith(42, { document_type: 'SELFIE', object_key: 'kyc/1/42/selfie/abc' });
    expect(completedSpy).toHaveBeenCalled();
  });

  it('surfaces a submit-failed error and does not emit completed when the backend call fails', async () => {
    kycServiceStub.requestDocumentUpload.and.rejectWith(new Error('network'));
    const completedSpy = jasmine.createSpy('completed');
    fixture.componentInstance.completed.subscribe(completedSpy);
    fixture.componentInstance.capturedImage.set(
      'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
    );

    await fixture.componentInstance.submit();

    expect(completedSpy).not.toHaveBeenCalled();
    expect(fixture.componentInstance.errorMessage()).toBeTruthy();
  });
});
