import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ApiService } from '../api/api.service';
import {
  AccessTokenClaims,
  AuthResponse,
  LoginRequest,
  LogoutRequest,
  MessageResponse,
  RefreshRequest,
  RegisterRequest,
  TokenPair,
  UserRole,
} from './auth.models';
import { decodeAccessToken, isTokenExpired } from './jwt.util';

const ACCESS_TOKEN_STORAGE_KEY = 'swadely.auth.access_token';
const REFRESH_TOKEN_STORAGE_KEY = 'swadely.auth.refresh_token';

/**
 * Signal-based auth state + calls to the backend's `/auth/*` endpoints
 * (`register`, `login`, `refresh`, `logout` -- Phase 1.2). Tokens persist to
 * `localStorage` so a page reload doesn't drop the session; `authInterceptor`
 * reads `accessToken()` to attach the `Authorization` header, and
 * `authGuard`/`roleGuard` read `isAuthenticated()`/`role()`.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiService);

  private readonly accessTokenSignal = signal<string | null>(this.readStorage(ACCESS_TOKEN_STORAGE_KEY));
  private readonly refreshTokenSignal = signal<string | null>(this.readStorage(REFRESH_TOKEN_STORAGE_KEY));
  private readonly claimsSignal = signal<AccessTokenClaims | null>(
    this.decodeStoredClaims(this.readStorage(ACCESS_TOKEN_STORAGE_KEY))
  );

  readonly accessToken = this.accessTokenSignal.asReadonly();
  readonly claims = this.claimsSignal.asReadonly();

  readonly isAuthenticated = computed(() => {
    const claims = this.claimsSignal();
    return claims !== null && !isTokenExpired(claims);
  });

  readonly role = computed<UserRole | null>(() => this.claimsSignal()?.role ?? null);
  readonly email = computed<string | null>(() => this.claimsSignal()?.email ?? null);

  async register(request: RegisterRequest): Promise<AuthResponse> {
    const response = await firstValueFrom(this.api.post<AuthResponse>('/auth/register', request));
    this.applyTokens(response.tokens);
    return response;
  }

  async login(request: LoginRequest): Promise<AuthResponse> {
    const response = await firstValueFrom(this.api.post<AuthResponse>('/auth/login', request));
    this.applyTokens(response.tokens);
    return response;
  }

  /** Rotates the refresh token: the backend revokes the presented one and issues a new pair. */
  async refresh(): Promise<TokenPair> {
    const refreshToken = this.refreshTokenSignal();
    if (!refreshToken) {
      throw new Error('No refresh token available.');
    }
    const body: RefreshRequest = { refresh_token: refreshToken };
    const tokens = await firstValueFrom(this.api.post<TokenPair>('/auth/refresh', body));
    this.applyTokens(tokens);
    return tokens;
  }

  async logout(): Promise<void> {
    const refreshToken = this.refreshTokenSignal();
    if (refreshToken) {
      try {
        const body: LogoutRequest = { refresh_token: refreshToken };
        await firstValueFrom(this.api.post<MessageResponse>('/auth/logout', body));
      } catch {
        // Best-effort: the backend treats logout as idempotent even for an
        // already-revoked token, so a network failure here shouldn't block
        // clearing local session state.
      }
    }
    this.clearTokens();
  }

  getRefreshToken(): string | null {
    return this.refreshTokenSignal();
  }

  /** Stores a fresh token pair and re-derives claims/session state from it. Also used by
   * `authInterceptor` after a successful silent refresh. */
  applyTokens(tokens: TokenPair): void {
    this.accessTokenSignal.set(tokens.access_token);
    this.refreshTokenSignal.set(tokens.refresh_token);
    this.claimsSignal.set(decodeAccessToken(tokens.access_token));
    this.writeStorage(ACCESS_TOKEN_STORAGE_KEY, tokens.access_token);
    this.writeStorage(REFRESH_TOKEN_STORAGE_KEY, tokens.refresh_token);
  }

  clearTokens(): void {
    this.accessTokenSignal.set(null);
    this.refreshTokenSignal.set(null);
    this.claimsSignal.set(null);
    this.removeStorage(ACCESS_TOKEN_STORAGE_KEY);
    this.removeStorage(REFRESH_TOKEN_STORAGE_KEY);
  }

  private decodeStoredClaims(token: string | null): AccessTokenClaims | null {
    return token ? decodeAccessToken(token) : null;
  }

  private readStorage(key: string): string | null {
    if (typeof localStorage === 'undefined') {
      return null;
    }
    return localStorage.getItem(key);
  }

  private writeStorage(key: string, value: string): void {
    if (typeof localStorage === 'undefined') {
      return;
    }
    localStorage.setItem(key, value);
  }

  private removeStorage(key: string): void {
    if (typeof localStorage === 'undefined') {
      return;
    }
    localStorage.removeItem(key);
  }
}
