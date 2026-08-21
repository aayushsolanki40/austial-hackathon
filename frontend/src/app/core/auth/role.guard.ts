import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';
import { UserRole } from './auth.models';

/**
 * Factory for a functional route guard restricting access to any of
 * `roles`, read from the decoded access-token JWT's `role` claim
 * (`AuthService.role()`). Unauthenticated users are sent to `/login`;
 * authenticated users lacking the required role are sent to `/` rather than
 * shown a blank/broken admin shell.
 *
 * Usage: `canActivate: [roleGuard(['ADMIN'])]`.
 */
export function roleGuard(roles: UserRole[]): CanActivateFn {
  return (_route, state) => {
    const auth = inject(AuthService);
    const router = inject(Router);

    if (!auth.isAuthenticated()) {
      return router.createUrlTree(['/login'], { queryParams: { redirectTo: state.url } });
    }

    const currentRole = auth.role();
    if (currentRole && roles.includes(currentRole)) {
      return true;
    }

    return router.createUrlTree(['/']);
  };
}
