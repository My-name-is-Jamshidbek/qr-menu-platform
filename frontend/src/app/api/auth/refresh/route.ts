import {cookies} from 'next/headers';
import {NextResponse, type NextRequest} from 'next/server';

import {ApiError} from '@/lib/api';
import {clearSessionCookies, readRefreshToken, rotateTokens, writeSessionCookies} from '@/lib/auth';
import {
  RETURN_TO_PARAM,
  adminHome,
  adminLoginPath,
  localeFromPath,
  sanitiseReturnTo
} from '@/middleware-auth';

/**
 * `/api/auth/refresh` — swaps the refresh cookie for a new pair.
 *
 * Two entry points for two callers:
 *
 * - `GET` is the navigation path. The proxy redirects here when the access
 *   cookie has expired but the refresh cookie has not; this handler renews the
 *   pair and bounces the browser back to where it was heading, so the request
 *   is retried with cookies that are already fresh. Doing it as a redirect
 *   rather than inside the proxy keeps every token exchange on Node, where the
 *   API address is read at request time instead of baked in at build time.
 * - `POST` is the programmatic path, for a client that wants to extend the
 *   session without navigating.
 *
 * Rotation is on and the previous refresh token is blacklisted, so a failed
 * exchange is terminal: both cookies are dropped and the user signs in again.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type RefreshFailure = {error: 'session_expired' | 'unavailable'};

async function renew(): Promise<{ok: true} | {ok: false; expired: boolean}> {
  const refreshToken = await readRefreshToken();
  const store = await cookies();

  if (!refreshToken) {
    clearSessionCookies(store);
    return {ok: false, expired: true};
  }

  try {
    writeSessionCookies(store, await rotateTokens(refreshToken));
    return {ok: true};
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 400)) {
      clearSessionCookies(store);
      return {ok: false, expired: true};
    }
    return {ok: false, expired: false};
  }
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  const returnTo = sanitiseReturnTo(request.nextUrl.searchParams.get(RETURN_TO_PARAM));
  const locale = localeFromPath(returnTo);
  const outcome = await renew();

  if (outcome.ok) {
    return NextResponse.redirect(new URL(returnTo ?? adminHome(locale), request.url));
  }

  return NextResponse.redirect(new URL(adminLoginPath(locale, returnTo), request.url));
}

export async function POST(): Promise<NextResponse<RefreshFailure | null>> {
  const outcome = await renew();

  if (outcome.ok) return new NextResponse(null, {status: 204});

  return NextResponse.json<RefreshFailure>(
    {error: outcome.expired ? 'session_expired' : 'unavailable'},
    {status: outcome.expired ? 401 : 502}
  );
}
