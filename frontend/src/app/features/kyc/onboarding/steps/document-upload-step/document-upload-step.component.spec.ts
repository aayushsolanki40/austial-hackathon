import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideNoopAnimations } from '@angular/platform-browser/animations';

import { KycSubmission } from '../../../../../core/kyc/kyc.models';
import { KycService } from '../../../../../core/kyc/kyc.service';
import { DocumentUploadStepComponent } from './document-upload-step.component';

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

function fakeFile(name = 'passport.png'): File {
  return new File(['fake-bytes'], name, { type: 'image/png' });
}

function fakeChangeEvent(file: File): Event {
  const input = document.createElement('input');
  input.type = 'file';
  Object.defineProperty(input, 'files', { value: [file] });
  return { target: input } as unknown as Event;
}

describe('DocumentUploadStepComponent', () => {
  let fixture: ComponentFixture<DocumentUploadStepComponent>;
  let kycServiceStub: {
    submission: () => KycSubmission | null;
    requestDocumentUpload: jasmine.Spy;
    uploadToPresignedUrl: jasmine.Spy;
    confirmDocumentUpload: jasmine.Spy;
  };

  beforeEach(async () => {
    kycServiceStub = {
      submission: signal(draftSubmission()).asReadonly(),
      requestDocumentUpload: jasmine.createSpy('requestDocumentUpload'),
      uploadToPresignedUrl: jasmine.createSpy('uploadToPresignedUrl'),
      confirmDocumentUpload: jasmine.createSpy('confirmDocumentUpload'),
    };

    await TestBed.configureTestingModule({
      imports: [DocumentUploadStepComponent],
      providers: [provideNoopAnimations(), { provide: KycService, useValue: kycServiceStub }],
    }).compileComponents();

    fixture = TestBed.createComponent(DocumentUploadStepComponent);
    fixture.detectChanges();
  });

  it('does not allow continuing until both required documents are uploaded', () => {
    expect(fixture.componentInstance.allUploaded()).toBeFalse();
  });

  it('runs the presign -> direct upload -> confirm flow against the current submission and marks the slot uploaded', async () => {
    kycServiceStub.requestDocumentUpload.and.resolveTo({ upload_url: 'https://s3.example.com/obj', object_key: 'kyc/1/42/passport/abc' });
    kycServiceStub.uploadToPresignedUrl.and.resolveTo(undefined);
    kycServiceStub.confirmDocumentUpload.and.resolveTo({
      id: 1,
      document_type: 'PASSPORT',
      object_key: 'kyc/1/42/passport/abc',
      ocr_result: null,
      created_at: '2026-01-01T00:00:00Z',
    });

    const file = fakeFile();
    await fixture.componentInstance.onFileSelected('PASSPORT', fakeChangeEvent(file));

    expect(kycServiceStub.requestDocumentUpload).toHaveBeenCalledWith(42, { document_type: 'PASSPORT', content_type: 'image/png' });
    expect(kycServiceStub.uploadToPresignedUrl).toHaveBeenCalledWith('https://s3.example.com/obj', file, 'image/png');
    expect(kycServiceStub.confirmDocumentUpload).toHaveBeenCalledWith(42, { document_type: 'PASSPORT', object_key: 'kyc/1/42/passport/abc' });
    expect(fixture.componentInstance.stateFor('PASSPORT').status).toBe('uploaded');
  });

  it('marks the slot as errored when the upload flow fails', async () => {
    kycServiceStub.requestDocumentUpload.and.rejectWith(new Error('network'));

    await fixture.componentInstance.onFileSelected('PASSPORT', fakeChangeEvent(fakeFile()));

    expect(fixture.componentInstance.stateFor('PASSPORT').status).toBe('error');
  });

  it('emits completed only once both required documents are uploaded', async () => {
    kycServiceStub.requestDocumentUpload.and.resolveTo({ upload_url: 'https://s3.example.com/obj', object_key: 'kyc/1/42/doc/abc' });
    kycServiceStub.uploadToPresignedUrl.and.resolveTo(undefined);
    kycServiceStub.confirmDocumentUpload.and.resolveTo({
      id: 1,
      document_type: 'PASSPORT',
      object_key: 'kyc/1/42/doc/abc',
      ocr_result: null,
      created_at: '2026-01-01T00:00:00Z',
    });

    const completedSpy = jasmine.createSpy('completed');
    fixture.componentInstance.completed.subscribe(completedSpy);

    await fixture.componentInstance.onFileSelected('PASSPORT', fakeChangeEvent(fakeFile('passport.png')));
    fixture.componentInstance.continue();
    expect(completedSpy).not.toHaveBeenCalled();

    await fixture.componentInstance.onFileSelected('PROOF_OF_ADDRESS', fakeChangeEvent(fakeFile('bill.png')));
    fixture.componentInstance.continue();
    expect(completedSpy).toHaveBeenCalled();
  });
});
