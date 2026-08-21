import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { environment } from '../../../../environments/environment';
import AdminDashboardComponent from './admin-dashboard.component';

describe('AdminDashboardComponent', () => {
  let fixture: ComponentFixture<AdminDashboardComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdminDashboardComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(AdminDashboardComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('shows a loading state, then KPI cards on success', () => {
    fixture.detectChanges();
    expect(fixture.componentInstance.state()).toBe('loading');

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/admin/dashboard/summary`);
    req.flush({
      aum_usd: 1000,
      investor_count: 5,
      active_issuances: 1,
      pending_kyc_count: 2,
      open_aml_alert_count: 0,
    });
    fixture.detectChanges();

    expect(fixture.componentInstance.state()).toBe('loaded');
  });

  it('falls back to the error state when the endpoint is unavailable (not shipped yet)', () => {
    fixture.detectChanges();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/admin/dashboard/summary`);
    req.flush('not found', { status: 404, statusText: 'Not Found' });
    fixture.detectChanges();

    expect(fixture.componentInstance.state()).toBe('error');
  });
});
