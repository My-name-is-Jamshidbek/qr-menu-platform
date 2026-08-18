import 'server-only';

import {apiFetch} from '@/lib/api';
import {SessionExpiredError, readAccessToken} from '@/lib/auth';
import type {AppLocale} from '@/i18n/routing';
import type {components} from '@/types/api';

import {
  PRODUCTS_PAGE_SIZE,
  REQUIRED_CONTENT_LANGUAGE,
  SEARCH_SCAN_LIMIT,
  type ContentLanguage
} from './constants';
import type {
  AdminCategory,
  AdminProduct,
  AdminStats,
  CategoryOption,
  ProductPage,
  ProductQuery
} from './types';

/**
 * Read side of the admin panel.
 *
 * Every function here runs on the server with the access token taken from the
 * httpOnly cookie, so no admin endpoint is ever addressable from the browser.
 * Responses are fetched with `cache: 'no-store'`: staff must see what they just
 * saved, not a cached page from before the edit.
 */

type PaginatedProducts = components['schemas']['PaginatedAdminProductList'];
type PaginatedCategories = components['schemas']['PaginatedAdminCategoryList'];

/** The API's own ceiling on `page_size`; used for the bulk reads below. */
const MAX_API_PAGE_SIZE = 100;

/**
 * The token for a read performed while rendering.
 *
 * Deliberately does *not* refresh: a Server Component cannot write cookies, so
 * a rotation performed here would blacklist the stored refresh token without
 * being able to persist its replacement. Renewal belongs to the proxy and the
 * `/api/auth/refresh` handler, which run before any of this.
 */
async function adminToken(): Promise<string> {
  const token = await readAccessToken();
  if (!token) throw new SessionExpiredError();
  return token;
}

/** Dashboard counters. */
export async function fetchStats(): Promise<AdminStats> {
  return apiFetch<AdminStats>('admin/stats/', {
    accessToken: await adminToken(),
    cache: 'no-store'
  });
}

/** Every category, ordered as the API orders them (`order`, then `id`). */
export async function fetchCategories(): Promise<AdminCategory[]> {
  const page = await apiFetch<PaginatedCategories>('admin/categories/', {
    accessToken: await adminToken(),
    query: {page_size: MAX_API_PAGE_SIZE},
    cache: 'no-store'
  });

  return page.results;
}

/** The name of a translated record in `locale`, falling back to Uzbek. */
export function translatedName(
  translations: readonly {language: ContentLanguage; name: string}[],
  locale: AppLocale
): string {
  const exact = translations.find((row) => row.language === locale && row.name.trim() !== '');
  if (exact) return exact.name;

  const fallback = translations.find((row) => row.language === REQUIRED_CONTENT_LANGUAGE);
  return fallback?.name ?? '';
}

/**
 * Categories flattened into `<select>` options: each section followed by its
 * own subsections, so the two-level tree survives a flat control.
 */
export function toCategoryOptions(
  categories: readonly AdminCategory[],
  locale: AppLocale
): CategoryOption[] {
  const sections = categories.filter((category) => (category.parent ?? null) === null);
  const childrenOf = new Map<number, AdminCategory[]>();

  for (const category of categories) {
    const parent = category.parent ?? null;
    if (parent === null) continue;
    const siblings = childrenOf.get(parent) ?? [];
    siblings.push(category);
    childrenOf.set(parent, siblings);
  }

  return sections.flatMap((section) => [
    {
      id: section.id,
      slug: section.slug ?? '',
      label: translatedName(section.translations, locale),
      isChild: false
    },
    ...(childrenOf.get(section.id) ?? []).map((child) => ({
      id: child.id,
      slug: child.slug ?? '',
      label: translatedName(child.translations, locale),
      isChild: true
    }))
  ]);
}

/**
 * Case- and accent-insensitive comparison key.
 *
 * The menu mixes Latin, Cyrillic and apostrophised Uzbek, so a plain
 * `toLowerCase()` would miss "Босс" for "босс" and "o‘tkir" for "o'tkir".
 */
function fold(value: string): string {
  return value
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/['’`ʻ]/g, '')
    .toLowerCase()
    .trim();
}

function matchesSearch(product: AdminProduct, needle: string): boolean {
  if (fold(product.slug ?? '').includes(needle)) return true;

  return product.translations.some(
    (translation) =>
      fold(translation.name).includes(needle) ||
      fold(translation.description ?? '').includes(needle)
  );
}

function requestProducts(
  accessToken: string,
  query: {page: number; pageSize: number; category: string}
): Promise<PaginatedProducts> {
  return apiFetch<PaginatedProducts>('admin/products/', {
    accessToken,
    query: {
      page: query.page,
      page_size: query.pageSize,
      category: query.category === '' ? undefined : query.category
    },
    cache: 'no-store'
  });
}

function emptyPage(pageSize: number): ProductPage {
  return {items: [], count: 0, page: 1, pageCount: 1, pageSize};
}

/**
 * One page of products.
 *
 * Without a search term this is a single paginated API call — the browser
 * receives 20 rows, never the whole menu the way the original did. With a
 * term, the match is still computed on the server: the admin list endpoint
 * filters by category only, so this walks the API in `page_size=100` chunks
 * (bounded by `SEARCH_SCAN_LIMIT`), filters, and then slices the requested
 * page. Either way exactly one page of rows is serialised to the client.
 */
export async function fetchProductPage(query: ProductQuery): Promise<ProductPage> {
  const accessToken = await adminToken();
  const pageSize = PRODUCTS_PAGE_SIZE;
  const needle = fold(query.search);

  if (needle === '') {
    const response = await requestProducts(accessToken, {
      page: Math.max(1, query.page),
      pageSize,
      category: query.category
    });

    const pageCount = Math.max(1, Math.ceil(response.count / pageSize));
    return {
      items: response.results,
      count: response.count,
      page: Math.min(Math.max(1, query.page), pageCount),
      pageCount,
      pageSize
    };
  }

  const matches: AdminProduct[] = [];
  let scanned = 0;
  let apiPage = 1;
  let hasMore = true;

  while (hasMore && scanned < SEARCH_SCAN_LIMIT) {
    const response = await requestProducts(accessToken, {
      page: apiPage,
      pageSize: MAX_API_PAGE_SIZE,
      category: query.category
    });

    scanned += response.results.length;
    matches.push(...response.results.filter((product) => matchesSearch(product, needle)));
    hasMore = Boolean(response.next) && response.results.length > 0;
    apiPage += 1;
  }

  if (matches.length === 0) return emptyPage(pageSize);

  const pageCount = Math.max(1, Math.ceil(matches.length / pageSize));
  const page = Math.min(Math.max(1, query.page), pageCount);
  const start = (page - 1) * pageSize;

  return {
    items: matches.slice(start, start + pageSize),
    count: matches.length,
    page,
    pageCount,
    pageSize
  };
}

/** A single product with all of its translations and photos. */
export async function fetchProduct(id: number): Promise<AdminProduct> {
  return apiFetch<AdminProduct>(`admin/products/${id}/`, {
    accessToken: await adminToken(),
    cache: 'no-store'
  });
}
