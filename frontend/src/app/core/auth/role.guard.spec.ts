import { TestBed } from '@angular/core/testing';
import { Router, UrlTree, provideRouter } from '@angular/router';

import { UserRole } from './auth.models';
import { AuthService } from './auth.service';
import { roleGuard } from './role.guard';

describe('roleGuard', () => {
  let authServiceStub: { isAuthenticated: () => boolean; role: () => UserRole | null };
  let router: Router;

  beforeEach(() => {
    authServiceStub = { isAuthenticated: () => true, role: () => 'INVESTOR' };
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: AuthService, useValue: authServiceStub }],
    });
    router = TestBed.inject(Router);
  });

  it('allows access when the current role is in the allowed list', () => {
    authServiceStub.role = () => 'ADMIN';
    const guard = roleGuard(['ADMIN']);
    const result = TestBed.runInInjectionContext(() => guard({} as never, { url: '/admin' } as never));
    expect(result).toBeTrue();
  });

  it('redirects to / when the current role is not in the allowed list', () => {
    authServiceStub.role = () => 'INVESTOR';
    const guard = roleGuard(['ADMIN']);
    const result = TestBed.runInInjectionContext(() =>
      guard({} as never, { url: '/admin' } as never)
    ) as UrlTree;
    expect(result instanceof UrlTree).toBeTrue();
    expect(router.serializeUrl(result)).toBe('/');
  });

  it('redirects to /login when not authenticated', () => {
    authServiceStub.isAuthenticated = () => false;
    const guard = roleGuard(['ADMIN']);
    const result = TestBed.runInInjectionContext(() =>
      guard({} as never, { url: '/admin' } as never)
    ) as UrlTree;
    expect(router.serializeUrl(result)).toContain('/login');
  });
});
