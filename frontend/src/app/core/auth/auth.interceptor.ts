import { HttpErrorResponse, HttpEvent, HttpHandlerFn, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { BehaviorSubject, Observable, catchError, filter, from, switchMap, take, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';

/** Never attach/refresh-retry the bearer token against the auth endpoints themselves --
 * they're either unauthenticated (register/login) or already carry their own token in
 * the body (refresh/logout use `refresh_token`, not the `Authorization` header). */
const AUTH_ENDPOINT_SEGMENTS = ['/auth/register', '/auth/login', '/auth/refresh', '/auth/logout'];

// Module-level (not per-injection) so concurrent requests during a single refresh share
// one in-flight refresh call instead of each triggering its own.
let refreshInProgress = false;
const refreshedAccessToken$ = new BehaviorSubject<string | null>(null);

function isApiRequest(url: string): boolean {
  return url.startsWith(environment.apiBaseUrl);
}

function isAuthEndpoint(url: string): boolean {
  return AUTH_ENDPOINT_SEGMENTS.some((segment) => url.includes(segment));
}

function withBearerToken(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}

/**
 * Attaches `Authorization: Bearer <access_token>` to every request bound for
 * `environment.apiBaseUrl` (except the auth endpoints themselves). On a 401
 * from a token-bearing request, attempts one silent refresh via
 * `AuthService.refresh()` and retries the original request; if the refresh
 * itself fails, clears the session so `authGuard` redirects to login on the
 * next navigation.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);

  const attachesToken = isApiRequest(req.url) && !isAuthEndpoint(req.url);
  const token = auth.accessToken();
  const outgoing = attachesToken && token ? withBearerToken(req, token) : req;

  return next(outgoing).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401 && attachesToken && auth.getRefreshToken()) {
        return refreshAndRetry(outgoing, next, auth);
      }
      return throwError(() => error);
    })
  );
};

function refreshAndRetry(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
  auth: AuthService
): Observable<HttpEvent<unknown>> {
  if (!refreshInProgress) {
    refreshInProgress = true;
    refreshedAccessToken$.next(null);

    return from(auth.refresh()).pipe(
      switchMap((tokens) => {
        refreshInProgress = false;
        refreshedAccessToken$.next(tokens.access_token);
        return next(withBearerToken(req, tokens.access_token));
      }),
      catchError((refreshError: unknown) => {
        refreshInProgress = false;
        auth.clearTokens();
        return throwError(() => refreshError);
      })
    );
  }

  // A refresh triggered by a different concurrent request is already in flight --
  // wait for it to complete and reuse its result instead of refreshing twice.
  return refreshedAccessToken$.pipe(
    filter((token): token is string => token !== null),
    take(1),
    switchMap((token) => next(withBearerToken(req, token)))
  );
}
