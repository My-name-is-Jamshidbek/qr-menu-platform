'use server';

import {revalidatePath} from 'next/cache';
import {redirect} from 'next/navigation';
import {getTranslations} from 'next-intl/server';

import {defaultLocale, isAppLocale, type AppLocale} from '@/i18n/routing';
import {ApiError, apiFetch} from '@/lib/api';
import {SessionExpiredError, requireAccessToken} from '@/lib/auth';
import {adminLoginPath} from '@/middleware-auth';
import type {components} from '@/types/api';

import {
  CONTENT_LANGUAGES,
  MIN_PRICE_UZS,
  REQUIRED_CONTENT_LANGUAGE,
  type ContentLanguage
} from './constants';
import type {AdminActionState, AdminProduct, ProductTranslation} from './types';

/**
 * Write side of the admin panel.
 *
 * Every mutation is a Server Action: the form posts to Next.js, which attaches
 * the bearer token from the httpOnly cookie and calls Django. No admin write
 * is reachable from the browser, and the forms keep working with JavaScript
 * still loading.
 */

type ProductRequest = components['schemas']['AdminProductRequest'];
type PatchedProductRequest = components['schemas']['PatchedAdminProductRequest'];
type PaginatedProducts = components['schemas']['PaginatedAdminProductList'];

const PRODUCTS_ROUTE = '/[locale]/admin/products';
const PRODUCT_DETAIL_ROUTE = '/[locale]/admin/products/[id]';

function readLocale(formData: FormData): AppLocale {
  const value = formData.get('locale');
  return typeof value === 'string' && isAppLocale(value) ? value : defaultLocale;
}

function readText(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === 'string' ? value.trim() : '';
}

function readId(formData: FormData, key: string): number | null {
  const value = Number.parseInt(readText(formData, key), 10);
  return Number.isSafeInteger(value) && value > 0 ? value : null;
}

/** Refreshes both the list and the edit screen after any product write. */
function revalidateProductViews(): void {
  revalidatePath(PRODUCTS_ROUTE, 'page');
  revalidatePath(PRODUCT_DETAIL_ROUTE, 'page');
  revalidatePath('/[locale]/admin', 'page');
}

/**
 * Turns an API failure into form state.
 *
 * DRF reports nested translation problems under `translations`, which is not a
 * field the editor renders; those are surfaced on the required language's name
 * input instead, where the person can actually act on them.
 */
function toActionState(error: unknown, genericMessage: string): AdminActionState {
  if (error instanceof ApiError) {
    const fieldErrors = {...error.fieldErrors};

    if (fieldErrors.translations) {
      fieldErrors[`name_${REQUIRED_CONTENT_LANGUAGE}`] = fieldErrors.translations;
      delete fieldErrors.translations;
    }

    return {
      status: 'error',
      message: error.status === 400 ? undefined : error.message || genericMessage,
      fieldErrors
    };
  }

  return {status: 'error', message: genericMessage};
}

/** Collects the non-empty translations, and the languages left half-filled. */
function readTranslations(formData: FormData): {
  rows: ProductTranslation[];
  namelessDescriptions: ContentLanguage[];
} {
  const rows: ProductTranslation[] = [];
  const namelessDescriptions: ContentLanguage[] = [];

  for (const language of CONTENT_LANGUAGES) {
    const name = readText(formData, `name_${language}`);
    const description = readText(formData, `description_${language}`);

    if (name !== '') {
      rows.push({language, name, description});
    } else if (description !== '') {
      // A translation row cannot exist without a name, so a description typed
      // against a nameless language would be silently thrown away on save.
      namelessDescriptions.push(language);
    }
  }

  return {rows, namelessDescriptions};
}

/**
 * Creates or updates a product, translations included, in one request.
 *
 * The API writes the product and all three translation rows inside a single
 * transaction, which is why the whole multi-language form is one submit rather
 * than a tab per language with its own save button.
 */
export async function saveProductAction(
  _previous: AdminActionState,
  formData: FormData
): Promise<AdminActionState> {
  const locale = readLocale(formData);
  const t = await getTranslations({locale, namespace: 'admin'});
  const productId = readId(formData, 'id');

  const category = readId(formData, 'category');
  const priceText = readText(formData, 'price');
  const price = Number.parseInt(priceText, 10);
  const order = Number.parseInt(readText(formData, 'order'), 10);

  const {rows, namelessDescriptions} = readTranslations(formData);
  const fieldErrors: Record<string, string[]> = {};

  for (const language of namelessDescriptions) {
    fieldErrors[`name_${language}`] = [t('form.errors.descriptionWithoutName')];
  }

  if (category === null) {
    fieldErrors.category = [t('form.errors.categoryRequired')];
  }
  if (!Number.isSafeInteger(price) || price < MIN_PRICE_UZS) {
    fieldErrors.price = [t('form.errors.priceMin', {min: MIN_PRICE_UZS})];
  }
  if (!rows.some((row) => row.language === REQUIRED_CONTENT_LANGUAGE)) {
    fieldErrors[`name_${REQUIRED_CONTENT_LANGUAGE}`] = [t('form.errors.nameRequired')];
  }
  if (Object.keys(fieldErrors).length > 0) {
    return {status: 'error', message: t('form.errors.invalid'), fieldErrors};
  }

  const payload: ProductRequest = {
    category: category as number,
    price,
    is_available: formData.get('is_available') !== null,
    order: Number.isSafeInteger(order) && order >= 0 ? order : 0,
    translations: rows
  };

  let created: AdminProduct | null = null;

  try {
    const accessToken = await requireAccessToken();

    if (productId === null) {
      created = await apiFetch<AdminProduct>('admin/products/', {
        method: 'POST',
        accessToken,
        body: payload
      });
    } else {
      await apiFetch<AdminProduct>(`admin/products/${productId}/`, {
        method: 'PATCH',
        accessToken,
        body: payload satisfies PatchedProductRequest
      });
    }
  } catch (error) {
    if (error instanceof SessionExpiredError) redirect(adminLoginPath(locale, null));
    return toActionState(error, t('form.errors.saveFailed'));
  }

  revalidateProductViews();

  // `redirect` throws, so it stays outside the try block on purpose.
  if (created) redirect(`/${locale}/admin/products/${created.id}?created=1`);

  return {status: 'success', message: t('form.saved')};
}

/** Removes a product and its photos, then returns to the list. */
export async function deleteProductAction(formData: FormData): Promise<void> {
  const locale = readLocale(formData);
  const productId = readId(formData, 'id');
  if (productId === null) return;

  try {
    await apiFetch<void>(`admin/products/${productId}/`, {
      method: 'DELETE',
      accessToken: await requireAccessToken()
    });
  } catch (error) {
    if (error instanceof SessionExpiredError) redirect(adminLoginPath(locale, null));
    throw error;
  }

  revalidateProductViews();
  redirect(`/${locale}/admin/products?deleted=1`);
}

/**
 * Moves a product one place up or down within its category.
 *
 * Ordering is done with buttons rather than drag and drop: a drag target is
 * unusable by keyboard, invisible to a screen reader and painful on the phones
 * this panel is actually operated from. Two `order` values are swapped, so the
 * change is one small `PATCH` per row instead of a renumbering of the section.
 */
export async function moveProductAction(formData: FormData): Promise<void> {
  const locale = readLocale(formData);
  const productId = readId(formData, 'id');
  const direction = readText(formData, 'direction');
  if (productId === null || (direction !== 'up' && direction !== 'down')) return;

  try {
    const accessToken = await requireAccessToken();
    const current = await apiFetch<AdminProduct>(`admin/products/${productId}/`, {
      accessToken,
      cache: 'no-store'
    });

    const siblings = await apiFetch<PaginatedProducts>('admin/products/', {
      accessToken,
      query: {page_size: 100, category: readText(formData, 'category') || undefined},
      cache: 'no-store'
    });

    const ordered = siblings.results.filter((row) => row.category === current.category);
    const index = ordered.findIndex((row) => row.id === current.id);
    const neighbour = ordered[direction === 'up' ? index - 1 : index + 1];
    if (index === -1 || !neighbour) return;

    const currentOrder = current.order ?? 0;
    const neighbourOrder = neighbour.order ?? 0;

    if (currentOrder !== neighbourOrder) {
      await apiFetch<AdminProduct>(`admin/products/${current.id}/`, {
        method: 'PATCH',
        accessToken,
        body: {order: neighbourOrder} satisfies PatchedProductRequest
      });
      await apiFetch<AdminProduct>(`admin/products/${neighbour.id}/`, {
        method: 'PATCH',
        accessToken,
        body: {order: currentOrder} satisfies PatchedProductRequest
      });
    } else {
      // Equal `order` values are resolved by id, so one row has to be pushed
      // past the other. Only ever incrementing keeps the value non-negative.
      const [target, nextOrder] =
        direction === 'up'
          ? ([neighbour, currentOrder + 1] as const)
          : ([current, neighbourOrder + 1] as const);

      await apiFetch<AdminProduct>(`admin/products/${target.id}/`, {
        method: 'PATCH',
        accessToken,
        body: {order: nextOrder} satisfies PatchedProductRequest
      });
    }
  } catch (error) {
    if (error instanceof SessionExpiredError) redirect(adminLoginPath(locale, null));
    throw error;
  }

  revalidateProductViews();
}

/** Detaches a photo from a product; the API deletes the stored derivatives. */
export async function deleteProductImageAction(formData: FormData): Promise<void> {
  const locale = readLocale(formData);
  const productId = readId(formData, 'productId');
  const imageId = readId(formData, 'imageId');
  if (productId === null || imageId === null) return;

  try {
    await apiFetch<void>(`admin/products/${productId}/images/${imageId}/`, {
      method: 'DELETE',
      accessToken: await requireAccessToken()
    });
  } catch (error) {
    if (error instanceof SessionExpiredError) redirect(adminLoginPath(locale, null));
    throw error;
  }

  revalidateProductViews();
}
