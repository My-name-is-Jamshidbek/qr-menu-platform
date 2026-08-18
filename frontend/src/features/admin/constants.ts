import type {components} from '@/types/api';

/**
 * Values shared by the admin data layer, its Server Actions and its forms.
 * Keeping them in one module is what stops the list page, the form and the
 * actions from drifting apart on page size or on the language order.
 */

export type ContentLanguage = components['schemas']['LanguageEnum'];

/**
 * Every language a product can be written in, in the order the editor shows
 * them. `uz` leads because it is the required one and the API's fallback.
 */
export const CONTENT_LANGUAGES: readonly ContentLanguage[] = ['uz', 'ru', 'en'];

/** The language a product cannot be saved without. */
export const REQUIRED_CONTENT_LANGUAGE: ContentLanguage = 'uz';

/** Rows per page in the product list. The API caps `page_size` at 100. */
export const PRODUCTS_PAGE_SIZE = 20;

/**
 * Upper bound on the rows the search pass may pull from the API. The admin
 * list endpoint has no `search` parameter, so matching happens on the Next.js
 * server; this keeps that pass bounded no matter how the menu grows.
 */
export const SEARCH_SCAN_LIMIT = 1000;

/** `MinValueValidator(100)` on `Product.price`, mirrored for instant feedback. */
export const MIN_PRICE_UZS = 100;

/** Matches the API's 8 MB upload cap, checked before the bytes are sent. */
export const MAX_IMAGE_BYTES = 8 * 1024 * 1024;

/** Image types the API accepts; anything else is rejected in the browser. */
export const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/avif'];

/** Query-string keys of the product list, shared by the toolbar and the page. */
export const LIST_PARAMS = {
  page: 'page',
  search: 'q',
  category: 'category'
} as const;

/** Message keys under `admin.login.errors`, one per way a sign-in can fail. */
export type LoginErrorKey = 'invalidRequest' | 'invalidCredentials' | 'unavailable' | 'throttled';

/**
 * Maps the `?error=` code produced by the no-script login POST onto a message
 * key. Lives here, outside the client component, so the login page — a Server
 * Component — can call it while rendering.
 */
export function loginErrorKeyFromParam(value: string | undefined): LoginErrorKey | null {
  if (value === 'invalid_request') return 'invalidRequest';
  if (value === 'invalid_credentials') return 'invalidCredentials';
  if (value === 'unavailable') return 'unavailable';
  return null;
}
