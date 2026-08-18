import type {components} from '@/types/api';

/**
 * Menu shapes, aliased from the generated OpenAPI types.
 *
 * Per `docs/API_CONTRACT.md` a response type is never hand-written: these are
 * projections of `src/types/api.d.ts`, which `npm run gen:api` regenerates from
 * the live `drf-spectacular` schema. If the API changes shape, this file stops
 * compiling instead of silently drifting.
 */

/** Payload of `GET /api/v1/menu/`. */
export type MenuResponse = components['schemas']['Menu'];

/** A top-level section, with its subsections and every product beneath it. */
export type MenuCategory = components['schemas']['MenuCategory'];

/** A second-level category: a label only. */
export type MenuSubcategory = components['schemas']['Subcategory'];

/** A product as the storefront reads it, already resolved to one language. */
export type MenuProduct = components['schemas']['PublicProduct'];

/** A photo and its WebP derivatives. `srcset` is keyed by width in pixels. */
export type MenuImage = components['schemas']['Image'];

/**
 * One titled run of products, rendered as a heading plus a grid.
 *
 * The unfiltered menu produces one group per section; a section with
 * subsections produces one group per subsection. Grouping is decided on the
 * server so the client only ever renders what it is handed.
 */
export interface ProductGroup {
  /** Category slug the group came from. Unique within a view; used as the key. */
  slug: string;
  /** Already-translated section name. */
  name: string;
  products: MenuProduct[];
}

/**
 * Everything the page needs after the URL has been resolved against the menu.
 * Built by `resolveMenuView`, consumed by both the page and `generateMetadata`.
 */
export interface MenuView {
  /** The selected section, or `null` on the unfiltered `/menu` route. */
  category: MenuCategory | null;
  /** The selected subsection, or `null` when a whole section is shown. */
  subcategory: MenuSubcategory | null;
  /** Product groups to render, in menu order. */
  groups: ProductGroup[];
  /** Total products across every group — the set search runs over. */
  productCount: number;
}
