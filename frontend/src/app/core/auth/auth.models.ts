/**
 * Request/response shapes for `/auth/*`, mirrored from
 * `backend/src/modules/auth/auth_dto.py` -- keep these two in sync by hand
 * (no shared codegen between the Python and TypeScript sides yet).
 */

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface LogoutRequest {
  refresh_token: string;
}

/** One of the four roles defined in the build plan's `@Roles(...)` set (Phase 1.4). */
export type UserRole = 'INVESTOR' | 'ISSUER' | 'COMPLIANCE_OFFICER' | 'ADMIN';

export interface AuthUser {
  id: number;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: AuthUser;
  tokens: TokenPair;
}

export interface MessageResponse {
  message: string;
}

/** Decoded shape of the access-token JWT payload (see `AuthService._encode` in the backend). */
export interface AccessTokenClaims {
  sub: string;
  email: string;
  role: UserRole;
  type: 'access' | 'refresh';
  iat: number;
  exp: number;
  jti: string;
}
