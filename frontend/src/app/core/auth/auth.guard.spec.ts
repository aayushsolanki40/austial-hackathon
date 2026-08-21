import { TestBed } from '@angular/core/testing';
import { Router, UrlTree, provideRouter } from '@angular/router';

import { authGuard } from './auth.guard';
import { AuthService } from './auth.service';

describe('authGuard', () => {
  let authServiceStub: { isAuthenticated: () => boolean };
  let router: Router;

  beforeEach(() => {
    authServiceStub = { isAuthenticated: () => false };
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: AuthService, useValue: authServiceStub }],
    });
    router = TestBed.inject(Router);
  });

  it('allows navigation when authenticated', () => {
    authServiceStub.isAuthenticated = () => true;
    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as never, { url: '/portfolio' } as never)
    );
    expect(result).toBeTrue();
  });

  it('redirects to /login when not authenticated', () => {
    authServiceStub.isAuthenticated = () => false;
    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as never, { url: '/portfolio' } as never)
    ) as UrlTree;
    expect(result instanceof UrlTree).toBeTrue();
    expect(router.serializeUrl(result)).toContain('/login');
  });
});
