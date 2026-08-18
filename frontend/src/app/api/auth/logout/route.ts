import {cookies} from 'next/headers';
import {NextResponse} from 'next/server';

import {clearSessionCookies} from '@/lib/auth';

/**
 * `POST /api/auth/logout` — drops both session cookies.
 *
 * Nothing is sent to Django: the refresh token is rotated and blacklisted on
 * every renewal anyway, and the copy being discarded here is the only one that
 * ever existed outside the API. Clearing the cookies is therefore the whole of
 * signing out, and it cannot fail.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(): Promise<NextResponse> {
  clearSessionCookies(await cookies());
  return new NextResponse(null, {status: 204});
}
