import {NextResponse, type NextRequest} from 'next/server';

import {defaultLocale, isAppLocale} from '@/i18n/routing';

/**
 * Session cookie contract and the edge-side admin route guard.
 *
 * This module is deliberately dependency-free apart from `next/server` and the
 * locale list: it is bundled into the edge proxy, where `next/headers`, the
 * `server-only` marker and runtime `process.env` lookups are all unavailable.
 * Every token exchange therefore happens in the `/api/auth/*` route handlers,
 * which run on Node and can read the API address at request time.
 */

/** Short-lived JWT used as `Authorization: Bearer` on server-side API calls. */
export const ACCESS_COOKIE = 'bk_access';
/** Long-lived rotating token, only ever read by `/api/auth/refresh`. */
export const REFRESH_COOKIE = 'bk_refresh';

/** Mirrors `SIMPLE_JWT.ACCESS_TOKEN_LIFETIME` (15 minutes). */
export const ACCESS_MAX_AGE_SECONDS = 15 * 60;
/** Mirrors `SIMPLE_JWT.REFRESH_TOKEN_LIFETIME` (7 days). */
export const REFRESH_MAX_AGE_SECONDS = 7 * 24 * 60 * 60;

/**
 * Flags shared by both session cookies.
 *
 * `httpOnly` is the whole point of the Backend-For-Frontend: no script, first
 * or third party, can read a token, so an XSS bug cannot exfiltrate the
 * session. `secure` is unconditional — every browser treats `http://localhost`
 * as a trustworthy origin, so development still works while a deployment over
 * plain HTTP fails loudly instead of silently downgrading. `sameSite: 'lax'`
 * keeps the cookie off cross-site sub-requests while still allowing a normal
 * top-level navigation into the panel.
 */
export const SESSION_COOKIE_OPTIONS = {
  httpOnly: true,
  secure: true,
  sameSite: 'lax',
  path: '/'
} as const;

/** Where the login form lives, relative to a locale prefix. */
const LOGIN_PATH = '/admin/login';

/** Query parameter carrying the URL to return to after a successful login. */
export const RETURN_TO_PARAM = 'next';

/** Route handler that swaps the refresh cookie for a fresh access cookie. */
const REFRESH_ROUTE = '/api/auth/refresh';

type AdminRoute = {
  locale: string;
  /** `true` for the login screen itself, which must stay reachable signed out. */
  isLogin: boolean;
};

/**
 * Recognises `/<locale>/admin[/...]`. Returns `null` for everything else, which
 * is the vast majority of requests — the guard must be cheap.
 */
function matchAdminRoute(pathname: string): AdminRoute | null {
  const [, maybeLocale, section] = pathname.split('/');

  if (!isAppLocale(maybeLocale) || section !== 'admin') return null;

  const rest = pathname.slice(`/${maybeLocale}`.length);
  return {locale: maybeLocale, isLogin: rest === LOGIN_PATH || rest.startsWith(`${LOGIN_PATH}/`)};
}

/**
 * Only same-origin, absolute-path targets survive. Without this check the
 * `?next=` parameter would be an open redirect straight out of the login form.
 */
export function sanitiseReturnTo(value: string | null): string | null {
  if (!value || !value.startsWith('/') || value.startsWith('//')) return null;
  return value;
}

/** The dashboard of a locale, used whenever there is no valid return target. */
export function adminHome(locale: string): string {
  const safeLocale = isAppLocale(locale) ? locale : defaultLocale;
  return `/${safeLocale}/admin`;
}

/**
 * The locale prefix of an application path, falling back to the default. Lets
 * a handler that only has a return URL still redirect into the right language.
 */
export function localeFromPath(path: string | null): string {
  const candidate = path?.split('/')[1];
  return isAppLocale(candidate) ? candidate : defaultLocale;
}

/** The login screen of a locale, optionally remembering where to come back to. */
export function adminLoginPath(locale: string, returnTo: string | null): string {
  const safeLocale = isAppLocale(locale) ? locale : defaultLocale;
  const query = returnTo ? `?${RETURN_TO_PARAM}=${encodeURIComponent(returnTo)}` : '';
  return `/${safeLocale}${LOGIN_PATH}${query}`;
}

function refreshUrl(request: NextRequest, returnTo: string): URL {
  const url = new URL(REFRESH_ROUTE, request.url);
  url.searchParams.set(RETURN_TO_PARAM, returnTo);
  return url;
}

/**
 * Wraps the next-intl proxy with the admin session guard.
 *
 * The guard runs first and only ever *redirects*; it never inspects a token's
 * contents and never calls the API, so locale negotiation keeps working
 * untouched for every non-admin URL. Real verification happens in the admin
 * layout, which asks the API who the bearer is — this is the cheap pre-filter
 * that keeps an expired session from rendering a flash of the panel.
 */
export function withAdminAuth(
  intlProxy: (request: NextRequest) => NextResponse | Promise<NextResponse>
): (request: NextRequest) => Promise<NextResponse> {
  return async function proxy(request: NextRequest): Promise<NextResponse> {
    const route = matchAdminRoute(request.nextUrl.pathname);

    if (route) {
      const hasAccess = request.cookies.has(ACCESS_COOKIE);
      const hasRefresh = request.cookies.has(REFRESH_COOKIE);
      const here = `${request.nextUrl.pathname}${request.nextUrl.search}`;

      if (route.isLogin) {
        // Already signed in: sending the user back to a login form they cannot
        // fail is worse than dropping them on the dashboard.
        if (hasAccess) {
          const returnTo =
            sanitiseReturnTo(request.nextUrl.searchParams.get(RETURN_TO_PARAM)) ??
            adminHome(route.locale);
          return NextResponse.redirect(new URL(returnTo, request.url));
        }
      } else if (!hasAccess) {
        // The access cookie expires with the token it carries, so its absence
        // alongside a refresh cookie means "renew", not "signed out".
        return NextResponse.redirect(
          hasRefresh
            ? refreshUrl(request, here)
            : new URL(adminLoginPath(route.locale, here), request.url)
        );
      }
    }

    return intlProxy(request);
  };
}
