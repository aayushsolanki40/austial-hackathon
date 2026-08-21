import { jwtDecode } from 'jwt-decode';

import { AccessTokenClaims } from './auth.models';

/** Decodes an access-token JWT's payload without verifying the signature -- signature
 * verification is the backend's job (`JwtAuthGuard`); the frontend only ever reads the
 * claims to drive UI state (role-gated nav, `roleGuard`, expiry checks). */
export function decodeAccessToken(token: string): AccessTokenClaims | null {
  try {
    return jwtDecode<AccessTokenClaims>(token);
  } catch {
    return null;
  }
}

/** `exp` is seconds-since-epoch (standard JWT claim); `Date.now()` is milliseconds. */
export function isTokenExpired(claims: AccessTokenClaims, skewSeconds = 10): boolean {
  const nowSeconds = Date.now() / 1000;
  return claims.exp <= nowSeconds + skewSeconds;
}
