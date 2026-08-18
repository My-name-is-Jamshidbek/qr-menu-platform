import type {components} from '@/types/api';

import type {ContentLanguage} from './constants';

/**
 * Admin-facing slices of the generated OpenAPI schema, plus the few shapes the
 * UI adds on top of it. Nothing here is hand-written data from the API — every
 * response type is an alias into `src/types/api.d.ts`, which is generated from
 * `/api/schema/` by `npm run gen:api`.
 */

export type AdminStats = components['schemas']['Stats'];
export type AdminProduct = components['schemas']['AdminProduct'];
export type AdminProductImage = components['schemas']['AdminProductImage'];
export type AdminCategory = components['schemas']['AdminCategory'];
export type ProductTranslation = components['schemas']['ProductTranslation'];
export type CategoryTranslation = components['schemas']['CategoryTranslation'];
export type UploadedProductImage = components['schemas']['ProductImageUpload'];

/** One page of products, already resolved to the numbers the UI renders. */
export interface ProductPage {
  items: AdminProduct[];
  /** Total rows matching the current filters, across all pages. */
  count: number;
  /** 1-based, clamped into range. */
  page: number;
  pageCount: number;
  pageSize: number;
}

/** The filters a product list request can carry. */
export interface ProductQuery {
  page: number;
  search: string;
  /** Category *slug*, as the API filters on it. Empty means "all". */
  category: string;
}

/** A category flattened for a `<select>`: sections first, children indented. */
export interface CategoryOption {
  id: number;
  label: string;
  slug: string;
  /** `true` for a subsection, which the option list indents. */
  isChild: boolean;
}

/** The translation fields of one language as the form holds them. */
export interface TranslationDraft {
  language: ContentLanguage;
  name: string;
  description: string;
}

/**
 * Result of a Server Action, consumed through `useActionState`.
 *
 * `fieldErrors` is keyed the way the API keys them (`price`, `category`,
 * `translations`), plus the synthetic `name_<language>` keys the editor uses so
 * a per-language message can be shown next to the field that caused it.
 */
export interface AdminActionState {
  status: 'idle' | 'success' | 'error';
  /** Already-translated message, or a message key the caller resolves. */
  message?: string;
  fieldErrors?: Record<string, string[]>;
}

export const IDLE_ACTION_STATE: AdminActionState = {status: 'idle'};
