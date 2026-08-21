import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { DisclosureDocument } from '../../core/issuance/issuance.models';
import { DisclosureChecklistComponent } from './disclosure-checklist.component';

function doc(overrides: Partial<DisclosureDocument> = {}): DisclosureDocument {
  return {
    id: 1,
    disclosure_type: 'RISK',
    object_key: 'disclosures/1/risk.pdf',
    version: 1,
    is_current: true,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

const ALL_MISSING = ['RISK', 'FEE', 'LIQUIDITY', 'CUSTODY', 'TAX', 'PROSPECTUS'];

describe('DisclosureChecklistComponent', () => {
  let fixture: ComponentFixture<DisclosureChecklistComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DisclosureChecklistComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(DisclosureChecklistComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('shows 0 / 6 complete when every type is in missingDisclosureTypes', () => {
    fixture.componentInstance.proposalId = 1;
    fixture.componentInstance.disclosures = [];
    fixture.componentInstance.missingDisclosureTypes = ALL_MISSING;
    fixture.detectChanges();

    expect(fixture.componentInstance.completeCount()).toBe(0);
    expect(fixture.componentInstance.totalCount).toBe(6);
  });

  it('reflects the server-supplied missing list in the checklist, not the raw disclosures array', () => {
    fixture.componentInstance.proposalId = 1;
    fixture.componentInstance.disclosures = [doc({ disclosure_type: 'RISK' }), doc({ id: 2, disclosure_type: 'FEE' })];
    fixture.componentInstance.missingDisclosureTypes = ['LIQUIDITY', 'CUSTODY', 'TAX', 'PROSPECTUS'];
    fixture.detectChanges();

    expect(fixture.componentInstance.completeCount()).toBe(2);
    const risk = fixture.componentInstance.checklist().find((item) => item.type === 'RISK');
    expect(risk?.status).toBe('uploaded');
  });

  it('runs the presign -> S3 PUT -> confirm flow and emits uploaded on success', fakeAsync(() => {
    fixture.componentInstance.proposalId = 1;
    fixture.componentInstance.disclosures = [];
    fixture.componentInstance.missingDisclosureTypes = ALL_MISSING;
    fixture.componentInstance.uploadable = true;
    fixture.detectChanges();

    let uploadedEmitted = false;
    fixture.componentInstance.uploaded.subscribe(() => (uploadedEmitted = true));

    const file = new File(['%PDF-1.4'], 'risk.pdf', { type: 'application/pdf' });
    const input = { files: [file] } as unknown as HTMLInputElement;
    fixture.componentInstance.onFileSelected('RISK', { target: input } as unknown as Event);

    const presignReq = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1/disclosures/upload-url`);
    expect(presignReq.request.body).toEqual({ disclosure_type: 'RISK', content_type: 'application/pdf' });
    presignReq.flush({ upload_url: 'https://s3.example/presigned', object_key: 'disclosures/1/risk.pdf' });
    flushMicrotasks();

    const putReq = httpMock.expectOne('https://s3.example/presigned');
    expect(putReq.request.method).toBe('PUT');
    putReq.flush(null);
    flushMicrotasks();

    const confirmReq = httpMock.expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1/disclosures`);
    expect(confirmReq.request.body).toEqual({ disclosure_type: 'RISK', object_key: 'disclosures/1/risk.pdf' });
    confirmReq.flush(doc());
    flushMicrotasks();

    expect(uploadedEmitted).toBeTrue();
    expect(fixture.componentInstance.slotState('RISK')).toBe('idle');
  }));

  it('sets slot state to error when the presign request fails', fakeAsync(() => {
    fixture.componentInstance.proposalId = 1;
    fixture.componentInstance.disclosures = [];
    fixture.componentInstance.missingDisclosureTypes = ALL_MISSING;
    fixture.componentInstance.uploadable = true;
    fixture.detectChanges();

    const file = new File(['%PDF-1.4'], 'risk.pdf', { type: 'application/pdf' });
    const input = { files: [file] } as unknown as HTMLInputElement;
    fixture.componentInstance.onFileSelected('RISK', { target: input } as unknown as Event);

    httpMock
      .expectOne(`${environment.apiBaseUrl}/issuance/proposals/mine/1/disclosures/upload-url`)
      .flush('server error', { status: 500, statusText: 'Internal Server Error' });
    flushMicrotasks();

    expect(fixture.componentInstance.slotState('RISK')).toBe('error');
  }));
});
