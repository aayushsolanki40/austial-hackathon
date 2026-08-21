import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { environment } from '../../../../environments/environment';
import UserManagementComponent from './user-management.component';

describe('UserManagementComponent', () => {
  let fixture: ComponentFixture<UserManagementComponent>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserManagementComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(UserManagementComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('lists users returned by GET /admin/users', () => {
    fixture.detectChanges();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/admin/users`);
    req.flush([{ id: 1, email: '[email protected]', role: 'ADMIN', status: 'ACTIVE', created_at: '2026-01-01' }]);
    fixture.detectChanges();

    expect(fixture.componentInstance.state()).toBe('loaded');
    expect(fixture.componentInstance.users().length).toBe(1);
  });

  it('falls back to the error state when the endpoint is unavailable (not shipped yet)', () => {
    fixture.detectChanges();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/admin/users`);
    req.flush('not found', { status: 404, statusText: 'Not Found' });
    fixture.detectChanges();

    expect(fixture.componentInstance.state()).toBe('error');
  });
});
