import 'server-only';

import {cookies} from 'next/headers';

import type {components} from '@/types/api';
import {
  ACCESS_COOKIE,
  ACCESS_MAX_AGE_SECONDS,
  REFRESH_COOKIE,
  REFRESH_MAX_AGE_SECONDS,
  SESSION_COOKIE_OPTIONS
} from '@/middleware-auth';

import {ApiError, apiFetch} from './api';

/**
 * Session handling for the admin panel.
 *
 * The original application put the password in client JavaScript and marked a
 * visitor as logged in with `localStorage.adminToken = "authenticated"`. This
 * is the inverse: credentials are exchanged for a JWT pair on the Next.js
 * server, the pair is written to httpOnly cookies the browser cannot read, and
 * every admin API call is made from the server with the access token attached.
 * Nothing about the session is reachable from the document.
 */

export type SessionUser = components['schemas']['CurrentUser'];
type TokenPair = components['schemas']['TokenPairResponse'];
type RefreshedTokens = components['schemas']['TokenRefreshResponse'];

/** Raised when there is no usable session; callers turn it into a redirect. */
export class SessionExpiredError extends Error {
  constructor(message = 'The admin session is missing or no longer valid.') {
    super(message);
    this.name = 'SessionExpiredError';
  }
}

type MutableCookieStore = Awaited<ReturnType<typeof cookies>>;

/**
 * Writes the pair. The access cookie's `maxAge` matches the token lifetime, so
 * an expired token leaves no cookie behind and the proxy can tell "expired"
 * from "signed out" without decoding anything.
 */
export function writeSessionCookies(
  store: MutableCookieStore,
  tokens: {access: string; refresh?: string}
): void {
  store.set(ACCESS_COOKIE, tokens.access, {
    ...SESSION_COOKIE_OPTIONS,
    maxAge: ACCESS_MAX_AGE_SECONDS
  });

  if (tokens.refresh) {
    store.set(REFRESH_COOKIE, tokens.refresh, {
      ...SESSION_COOKIE_OPTIONS,
      maxAge: REFRESH_MAX_AGE_SECONDS
    });
  }
}

/** Removes both cookies with the same flags they were written with. */
export function clearSessionCookies(store: MutableCookieStore): void {
  store.set(ACCESS_COOKIE, '', {...SESSION_COOKIE_OPTIONS, maxAge: 0});
  store.set(REFRESH_COOKIE, '', {...SESSION_COOKIE_OPTIONS, maxAge: 0});
}

/** Exchanges credentials for a token pair. Throws `ApiError` (401) on failure. */
export function obtainTokens(username: string, password: string): Promise<TokenPair> {
  return apiFetch<TokenPair>('auth/token/', {
    method: 'POST',
    body: {username, password},
    cache: 'no-store'
  });
}

/** Rotates the refresh token. The API blacklists the one that was sent. */
export function rotateTokens(refresh: string): Promise<RefreshedTokens> {
  return apiFetch<RefreshedTokens>('auth/token/refresh/', {
    method: 'POST',
    body: {refresh},
    cache: 'no-store'
  });
}

/** The access token of the current request, or `null` when it has expired. */
export async function readAccessToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(ACCESS_COOKIE)?.value ?? null;
}

/** The refresh token of the current request, or `null`. */
export async function readRefreshToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(REFRESH_COOKIE)?.value ?? null;
}

/**
 * Asks the API who the bearer is.
 *
 * This is the only real verification in the system: the signature, the expiry
 * and the account's role are all checked by Django, so a forged or replayed
 * cookie cannot produce a session here.
 */
export async function fetchCurrentUser(accessToken: string): Promise<SessionUser | null> {
  try {
    return await apiFetch<SessionUser>('auth/me/', {accessToken, cache: 'no-store'});
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      return null;
    }
    throw error;
  }
}

/**
 * The verified account behind the current request, or `null`.
 *
 * Used by the admin layout, which is a Server Component: there is no client
 * guard anywhere in the panel, so an unauthenticated request never receives
 * admin markup in the first place.
 */
export async function getSessionUser(): Promise<SessionUser | null> {
  const accessToken = await readAccessToken();
  if (!accessToken) return null;
  return fetchCurrentUser(accessToken);
}

/**
 * The access token for a Server Action or Route Handler.
 *
 * Both run in a context where cookies are writable, so an expired access token
 * is renewed and persisted inline instead of bouncing the user through a
 * redirect the way a navigation does.
 *
 * @throws {SessionExpiredError} when no session can be established.
 */
export async function requireAccessToken(): Promise<string> {
  const store = await cookies();
  const accessToken = store.get(ACCESS_COOKIE)?.value;
  if (accessToken) return accessToken;

  const refreshToken = store.get(REFRESH_COOKIE)?.value;
  if (!refreshToken) throw new SessionExpiredError();

  try {
    const tokens = await rotateTokens(refreshToken);
    writeSessionCookies(store, tokens);
    return tokens.access;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      clearSessionCookies(store);
      throw new SessionExpiredError();
    }
    throw error;
  }
}
