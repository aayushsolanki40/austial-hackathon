import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(withInterceptors([authInterceptor])), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('attaches Authorization when an access token is present', () => {
    const auth = TestBed.inject(AuthService);
    auth.applyTokens({
      access_token: 'header.payload.sig',
      refresh_token: 'refresh',
      token_type: 'bearer',
      expires_in: 900,
    });

    http.get(`${environment.apiBaseUrl}/admin/users`).subscribe();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/admin/users`);
    expect(req.request.headers.get('Authorization')).toBe('Bearer header.payload.sig');
    req.flush([]);
  });

  it('does not attach Authorization to the login endpoint', () => {
    http.post(`${environment.apiBaseUrl}/auth/login`, {}).subscribe();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/auth/login`);
    expect(req.request.headers.has('Authorization')).toBeFalse();
    req.flush({});
  });
});
