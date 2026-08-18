'use server';

import {revalidatePath} from 'next/cache';
import {getTranslations} from 'next-intl/server';

import type {AppLocale} from '@/i18n/routing';
import {ApiError} from '@/lib/api';
import {readAccessToken} from '@/lib/auth';

import {
  createTable,
  deleteTable,
  fetchQrSheetPdfBase64,
  fetchTableQrSvg,
  updateTable
} from './api';
import type {ActionResult, AdminTable, TableFieldErrors, TableInput} from './types';

/**
 * Server actions behind the admin tables screen.
 *
 * They exist so the browser never holds a JWT: the client component posts a
 * plain object, the action reads the httpOnly cookie and talks to Django. Every
 * action resolves to an {@link ActionResult} rather than throwing, so a
 * duplicate table number lands under the input that caused it instead of
 * blowing up the error boundary.
 */

/** Fields of {@link TableInput} the API can report validation errors against. */
const INPUT_FIELDS = ['number', 'label', 'is_active'] as const;

function toFieldErrors(error: ApiError): TableFieldErrors {
  const fieldErrors: TableFieldErrors = {};

  for (const field of INPUT_FIELDS) {
    // The API's own message: DRF phrases these ("table with this number
    // already exists") and localises them from its own catalogue.
    const messages = error.fieldErrors[field];
    if (messages?.length) fieldErrors[field] = messages.join(' ');
  }

  return fieldErrors;
}

/**
 * Runs one authenticated admin operation and normalises every failure mode
 * — signed out, network down, validation rejected — into `ActionResult`.
 *
 * @param fallbackKey message shown when the API refuses without naming a field.
 */
async function run<TData>(
  locale: AppLocale,
  operation: (accessToken: string) => Promise<TData>,
  fallbackKey: 'saveFailed' | 'generic' = 'generic'
): Promise<ActionResult<TData>> {
  const t = await getTranslations({locale, namespace: 'common.errors'});
  const accessToken = await readAccessToken();

  if (!accessToken) {
    return {ok: false, message: t('unauthorized'), fieldErrors: {}};
  }

  try {
    return {ok: true, data: await operation(accessToken)};
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;

    if (error.isNetworkError) {
      return {ok: false, message: t('network'), fieldErrors: {}};
    }

    if (error.status === 401 || error.status === 403) {
      return {ok: false, message: t('unauthorized'), fieldErrors: {}};
    }

    const fieldErrors = toFieldErrors(error);
    return {
      ok: false,
      // A message that only repeats a field error would be noise in the toast.
      message: Object.keys(fieldErrors).length > 0 ? '' : t(fallbackKey),
      fieldErrors
    };
  }
}

/**
 * Creates a table, or updates the one with `id`.
 *
 * @param locale drives the error copy; a Server Action has no `[locale]`
 * segment to infer it from, so the caller passes the locale it is rendered in.
 */
export async function saveTableAction(
  locale: AppLocale,
  id: number | null,
  input: TableInput
): Promise<ActionResult<AdminTable>> {
  const result = await run(
    locale,
    (accessToken) =>
      id === null ? createTable(accessToken, input) : updateTable(accessToken, id, input),
    'saveFailed'
  );

  if (result.ok) revalidatePath(`/${locale}/admin/tables`);
  return result;
}

export async function deleteTableAction(
  locale: AppLocale,
  id: number
): Promise<ActionResult<undefined>> {
  const result = await run(locale, async (accessToken) => {
    await deleteTable(accessToken, id);
    return undefined;
  });

  if (result.ok) revalidatePath(`/${locale}/admin/tables`);
  return result;
}

/**
 * One table's QR code as SVG markup.
 *
 * Fetched on demand rather than with the list: a room of forty tables would
 * otherwise ship forty inline SVGs to a screen that shows one at a time.
 */
export async function fetchTableQrAction(
  locale: AppLocale,
  id: number
): Promise<ActionResult<string>> {
  return run(locale, (accessToken) => fetchTableQrSvg(accessToken, id));
}

/** The printable sheet of every active table's code, base64-encoded PDF. */
export async function fetchQrSheetAction(locale: AppLocale): Promise<ActionResult<string>> {
  return run(locale, (accessToken) => fetchQrSheetPdfBase64(accessToken));
}
