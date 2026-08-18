import {timingSafeEqual} from 'node:crypto';

import {revalidateTag} from 'next/cache';
import type {NextRequest} from 'next/server';

import {CACHE_TAGS} from '@/lib/api';

/**
 * ISR revalidation webhook.
 *
 * Django posts here on every successful write to a product, translation, image
 * or category (`apps/common/api/revalidate.py`), which is what makes a staff
 * edit appear on the statically generated menu within seconds instead of at the
 * next deploy. The call is fire-and-forget on the API side with a 2s timeout, so
 * this handler stays cheap and always answers.
 *
 *   POST /api/revalidate
 *   X-Revalidate-Secret: <REVALIDATE_SECRET>
 *   {"tags": ["menu"]}
 */

const SECRET_HEADER = 'X-Revalidate-Secret';

/** Only tags this app actually caches under may be purged. */
const ALLOWED_TAGS = new Set<string>(Object.values(CACHE_TAGS));

/**
 * Constant-time secret comparison.
 *
 * `===` on strings short-circuits at the first differing byte, which leaks the
 * shared secret to anyone who can time the response. `timingSafeEqual` needs
 * equal-length buffers, so unequal lengths are rejected first — that only
 * reveals the length, which is not the secret.
 */
function isValidSecret(provided: string | null, expected: string): boolean {
  if (!provided) return false;

  const providedBytes = Buffer.from(provided, 'utf8');
  const expectedBytes = Buffer.from(expected, 'utf8');

  if (providedBytes.length !== expectedBytes.length) return false;

  return timingSafeEqual(providedBytes, expectedBytes);
}

function parseTags(payload: unknown): string[] | null {
  if (typeof payload !== 'object' || payload === null) return null;

  const {tags} = payload as {tags?: unknown};

  if (!Array.isArray(tags) || tags.length === 0) return null;
  if (!tags.every((tag): tag is string => typeof tag === 'string')) return null;

  return tags;
}

export async function POST(request: NextRequest): Promise<Response> {
  const expected = process.env.REVALIDATE_SECRET;

  // Refusing outright beats defaulting to a well-known value: a deployment that
  // forgot the variable must not silently accept anonymous cache purges.
  if (!expected) {
    console.error('REVALIDATE_SECRET is not set; refusing to revalidate.');
    return Response.json({revalidated: false, reason: 'not_configured'}, {status: 503});
  }

  if (!isValidSecret(request.headers.get(SECRET_HEADER), expected)) {
    return Response.json({revalidated: false, reason: 'forbidden'}, {status: 401});
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return Response.json({revalidated: false, reason: 'invalid_json'}, {status: 400});
  }

  const tags = parseTags(payload);
  if (!tags) {
    return Response.json({revalidated: false, reason: 'invalid_tags'}, {status: 400});
  }

  const unknown = tags.filter((tag) => !ALLOWED_TAGS.has(tag));
  if (unknown.length > 0) {
    return Response.json(
      {revalidated: false, reason: 'unknown_tags', tags: unknown},
      {status: 400}
    );
  }

  for (const tag of tags) {
    // `{expire: 0}` rather than the `'max'` profile: this is a webhook telling
    // us the data is already wrong, so the next guest must not be served the
    // stale menu while a background refresh catches up.
    revalidateTag(tag, {expire: 0});
  }

  return Response.json({revalidated: true, tags, now: Date.now()});
}
