import {NextResponse, type NextRequest} from 'next/server';

import {recordTableScan} from '@/features/tables/api';
import {
  serializeTableSession,
  TABLE_COOKIE_MAX_AGE_SECONDS,
  TABLE_COOKIE_NAME
} from '@/features/tables/cookie';
import {LOCALE_COOKIE_NAME, negotiateLocale} from '@/features/tables/negotiate-locale';

/**
 * The URL printed inside every table's QR code.
 *
 * It is a Route Handler rather than a page for two reasons: only a handler may
 * write a cookie during a GET, and a guest pointing a camera at a sticker
 * should never see a rendered page before the menu — the whole route is one
 * redirect with a `Set-Cookie` on it.
 *
 * It deliberately sits outside the `[locale]` segment: the sticker cannot know
 * which language its reader speaks, so the language is negotiated here.
 */

/** Where a successful scan sends the guest, under the negotiated locale. */
const MENU_PATH = 'menu';

/** Sub-route shown when the token is unknown, retired or the API is unreachable. */
const UNAVAILABLE_SEGMENT = 'unavailable';

/** The API only ever mints v4 UUIDs; anything else is not worth a round trip. */
const TOKEN_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * A scan is a one-off event with a `Set-Cookie` attached: caching it anywhere
 * would hand the next guest the previous guest's table.
 */
function redirect(request: NextRequest, path: string): NextResponse {
  const response = NextResponse.redirect(new URL(path, request.nextUrl.origin), 307);
  response.headers.set('Cache-Control', 'no-store');
  return response;
}

export async function GET(
  request: NextRequest,
  {params}: RouteContext<'/t/[token]'>
): Promise<NextResponse> {
  const {token} = await params;
  const locale = negotiateLocale(
    request.cookies.get(LOCALE_COOKIE_NAME)?.value,
    request.headers.get('accept-language')
  );

  if (!TOKEN_PATTERN.test(token)) {
    return redirect(request, `/t/${encodeURIComponent(token)}/${UNAVAILABLE_SEGMENT}`);
  }

  let tableNumber: number;
  try {
    ({table_number: tableNumber} = await recordTableScan(token, locale));
  } catch {
    // Unknown token, retired table, throttled, or the API is down. The guest
    // gets the same friendly page for all of them — which of the four it was
    // is the operator's problem, not theirs.
    return redirect(request, `/t/${token}/${UNAVAILABLE_SEGMENT}`);
  }

  const response = redirect(request, `/${locale}/${MENU_PATH}`);

  response.cookies.set({
    name: TABLE_COOKIE_NAME,
    value: serializeTableSession({token, number: tableNumber}),
    httpOnly: true,
    sameSite: 'lax',
    // Unconditional, matching `SESSION_COOKIE_OPTIONS`: browsers treat
    // `http://localhost` as a trustworthy origin, so development still works
    // while a deployment over plain HTTP fails visibly instead of quietly
    // handing every guest an unprotected table claim.
    secure: true,
    path: '/',
    maxAge: TABLE_COOKIE_MAX_AGE_SECONDS
  });

  return response;
}
