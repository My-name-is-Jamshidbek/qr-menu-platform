import 'server-only';

import {apiFetch, ApiError} from '@/lib/api';

import type {AdminStats, AdminTable, TableInput, TablePage, TableScanResult} from './types';

/**
 * Server-side access to the `tables` endpoints.
 *
 * Everything under `/admin/` requires the `ADMIN` role and is therefore only
 * ever called from a Server Component or a Server Action, with the JWT taken
 * from the httpOnly cookie. The QR artwork endpoints return SVG and PDF rather
 * than JSON, so they bypass `apiFetch` and use `fetchAdminBinary` below.
 */

/** DRF's maximum `page_size`; there will never be more tables than that. */
const MAX_PAGE_SIZE = 100;

/** Records the scan behind a QR code and resolves the table number. */
export function recordTableScan(token: string, language: string): Promise<TableScanResult> {
  return apiFetch<TableScanResult>(`tables/${token}/scan/`, {
    method: 'POST',
    body: {language},
    // A guest is waiting on this redirect; do not sit on a stalled API.
    timeoutMs: 4_000
  });
}

/** Every table in one page — a dining room is far smaller than the page cap. */
export function listTables(accessToken: string): Promise<TablePage> {
  return apiFetch<TablePage>('admin/tables/', {
    accessToken,
    query: {page_size: MAX_PAGE_SIZE},
    cache: 'no-store'
  });
}

/** Dashboard counters. Used here only for the seven-day scan total. */
export function fetchAdminStats(accessToken: string): Promise<AdminStats> {
  return apiFetch<AdminStats>('admin/stats/', {accessToken, cache: 'no-store'});
}

export function createTable(accessToken: string, input: TableInput): Promise<AdminTable> {
  return apiFetch<AdminTable>('admin/tables/', {method: 'POST', body: input, accessToken});
}

export function updateTable(
  accessToken: string,
  id: number,
  input: TableInput
): Promise<AdminTable> {
  return apiFetch<AdminTable>(`admin/tables/${id}/`, {
    method: 'PATCH',
    body: input,
    accessToken
  });
}

export function deleteTable(accessToken: string, id: number): Promise<void> {
  return apiFetch<void>(`admin/tables/${id}/`, {method: 'DELETE', accessToken});
}

function binaryUrl(path: string): string {
  const baseUrl = process.env.API_INTERNAL_URL;

  if (!baseUrl) {
    throw new Error(
      'API_INTERNAL_URL is not set. It must point at the Django API base path, e.g. http://api:8000/api/v1'
    );
  }

  return `${baseUrl.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`;
}

/**
 * Fetches a non-JSON admin resource (the QR artwork endpoints).
 *
 * `Accept` stays at `*​/*`: the QR views write their `HttpResponse` by hand, but
 * DRF still runs content negotiation over the JSON renderer first, so asking
 * for `image/svg+xml` or `application/pdf` by name earns a 406.
 *
 * @throws {ApiError} shaped exactly like `apiFetch`'s, so callers handle one
 * error type regardless of which transport produced it.
 */
async function fetchAdminBinary(path: string, accessToken: string): Promise<ArrayBuffer> {
  let response: Response;

  try {
    response = await fetch(binaryUrl(path), {
      headers: {Accept: '*/*', Authorization: `Bearer ${accessToken}`},
      cache: 'no-store',
      // The PDF sheet renders one PNG per table, so it needs more than the
      // 10s a JSON call gets.
      signal: AbortSignal.timeout(20_000)
    });
  } catch (cause) {
    throw new ApiError({
      message: `Could not reach the API at ${path}`,
      status: 0,
      code: cause instanceof Error && cause.name === 'TimeoutError' ? 'timeout' : 'network_error',
      path,
      cause
    });
  }

  if (!response.ok) {
    throw new ApiError({
      message: response.statusText || 'API request failed',
      status: response.status,
      code: `http_${response.status}`,
      path
    });
  }

  return response.arrayBuffer();
}

/** One table's QR code as an SVG document, ready to inline or download. */
export async function fetchTableQrSvg(accessToken: string, id: number): Promise<string> {
  const bytes = await fetchAdminBinary(`admin/tables/${id}/qr.svg`, accessToken);
  return new TextDecoder().decode(bytes);
}

/**
 * The printable A4 sheet of every active table's code, base64-encoded.
 *
 * Base64 rather than bytes because a Server Action's return value crosses the
 * RSC boundary, where a `Uint8Array` is not a serialisable payload.
 */
export async function fetchQrSheetPdfBase64(accessToken: string): Promise<string> {
  const bytes = await fetchAdminBinary('admin/tables/qr-sheet.pdf', accessToken);
  return Buffer.from(bytes).toString('base64');
}
