import {revalidatePath} from 'next/cache';
import {NextResponse, type NextRequest} from 'next/server';

import {ACCEPTED_IMAGE_TYPES, MAX_IMAGE_BYTES} from '@/features/admin/constants';
import type {UploadedProductImage} from '@/features/admin/types';
import {ApiError, apiFetch} from '@/lib/api';
import {SessionExpiredError, requireAccessToken} from '@/lib/auth';

/**
 * `POST /<locale>/admin/products/<id>/images` — the one upload endpoint.
 *
 * It exists as a Route Handler rather than a Server Action because the browser
 * needs `XMLHttpRequest` upload progress events, and those require a request
 * the client controls. The handler adds the bearer token from the httpOnly
 * cookie and streams the file on to Django, which converts it to WebP at three
 * widths — so the browser gains a progress bar without gaining a token.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type UploadError = {error: 'unauthorised' | 'invalid_file' | 'too_large' | 'failed'};

function failure(error: UploadError['error'], status: number): NextResponse<UploadError> {
  return NextResponse.json<UploadError>({error}, {status});
}

export async function POST(
  request: NextRequest,
  context: {params: Promise<{locale: string; id: string}>}
): Promise<NextResponse<UploadedProductImage | UploadError>> {
  const {id} = await context.params;
  const productId = Number.parseInt(id, 10);
  if (!Number.isSafeInteger(productId) || productId <= 0) return failure('invalid_file', 400);

  let accessToken: string;
  try {
    accessToken = await requireAccessToken();
  } catch (error) {
    if (error instanceof SessionExpiredError) return failure('unauthorised', 401);
    throw error;
  }

  const submitted = await request.formData();
  const image = submitted.get('image');

  if (!(image instanceof File) || image.size === 0) return failure('invalid_file', 400);
  if (!ACCEPTED_IMAGE_TYPES.includes(image.type)) return failure('invalid_file', 415);
  // Checked again here because the browser-side check is a courtesy, not a control.
  if (image.size > MAX_IMAGE_BYTES) return failure('too_large', 413);

  const upstream = new FormData();
  upstream.set('image', image, image.name);
  upstream.set('alt', String(submitted.get('alt') ?? ''));
  if (submitted.get('is_primary') !== null) upstream.set('is_primary', 'true');

  try {
    const created = await apiFetch<UploadedProductImage>(`admin/products/${productId}/images/`, {
      method: 'POST',
      accessToken,
      body: upstream,
      // Image conversion at three widths takes longer than a JSON round trip.
      timeoutMs: 60_000
    });

    revalidatePath('/[locale]/admin/products/[id]', 'page');
    revalidatePath('/[locale]/admin/products', 'page');

    return NextResponse.json(created, {status: 201});
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return failure('invalid_file', 404);
    return failure('failed', 502);
  }
}
