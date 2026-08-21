import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { environment } from '../../../environments/environment';
import { AuthResponse, TokenPair } from './auth.models';
import { AuthService } from './auth.service';

function fakeJwt(claims: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(JSON.stringify(claims));
  return `${header}.${payload}.signature`;
}

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  it('starts unauthenticated with no stored tokens', () => {
    expect(service.isAuthenticated()).toBeFalse();
    expect(service.role()).toBeNull();
  });

  it('login() posts credentials and stores the returned token pair', async () => {
    const accessToken = fakeJwt({
      sub: '1',
      email: '[email protected]',
      role: 'INVESTOR',
      type: 'access',
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 900,
      jti: 'abc',
    });
    const response: AuthResponse = {
      user: { id: 1, email: '[email protected]', role: 'INVESTOR', created_at: '2026-01-01T00:00:00Z' },
      tokens: { access_token: accessToken, refresh_token: 'refresh-token', token_type: 'bearer', expires_in: 900 },
    };

    const promise = service.login({ email: '[email protected]', password: 'password123' });

    const req = httpMock.expectOne(`${environment.apiBaseUrl}/auth/login`);
    expect(req.request.method).toBe('POST');
    req.flush(response);

    await promise;

    expect(service.isAuthenticated()).toBeTrue();
    expect(service.role()).toBe('INVESTOR');
    expect(service.accessToken()).toBe(accessToken);
  });

  it('logout() clears session state even when the backend call fails', async () => {
    service.applyTokens({
      access_token: fakeJwt({
        sub: '1',
        email: '[email protected]',
        role: 'INVESTOR',
        type: 'access',
        iat: 0,
        exp: Math.floor(Date.now() / 1000) + 900,
        jti: 'x',
      }),
      refresh_token: 'refresh-token',
      token_type: 'bearer',
      expires_in: 900,
    } satisfies TokenPair);

    const promise = service.logout();
    const req = httpMock.expectOne(`${environment.apiBaseUrl}/auth/logout`);
    req.error(new ProgressEvent('network error'));

    await promise;

    expect(service.isAuthenticated()).toBeFalse();
    expect(service.accessToken()).toBeNull();
  });
});
