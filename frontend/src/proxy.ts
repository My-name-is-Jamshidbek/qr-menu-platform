import createIntlMiddleware from 'next-intl/middleware';

import {routing} from '@/i18n/routing';
import {withAdminAuth} from '@/middleware-auth';

/**
 * Locale negotiation. Runs before rendering and, for an unprefixed path,
 * redirects to the best match from the `NEXT_LOCALE` cookie, then the
 * `Accept-Language` header, then the default locale — so `/` becomes `/uz`.
 *
 * `proxy.ts` is the Next.js 16 name for what used to be `middleware.ts`.
 *
 * `withAdminAuth` composes on top: it short-circuits `/<locale>/admin/*` for a
 * visitor with no session cookie and otherwise hands the request straight to
 * the locale middleware, so language handling is identical on every route.
 */
export default withAdminAuth(createIntlMiddleware(routing));

export const config = {
  // Skip Next.js internals, the revalidation API, the QR entry point and
  // anything with a file extension; those must not be redirected into a locale
  // prefix. `/t/<token>` in particular is a bare route handler that resolves the
  // table and issues its own localised redirect — prefixing it here would send
  // the scan to `/<locale>/t/<token>`, which matches no route at all.
  matcher: ['/((?!api|t/|_next|_vercel|.*\\..*).*)']
};
