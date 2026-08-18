import type {
  MenuCategory,
  MenuProduct,
  MenuResponse,
  MenuSubcategory,
  MenuView,
  ProductGroup
} from './types';

/**
 * Turns the URL into the set of products to render.
 *
 * The filter lives in the path (`/uz/menu`, `/uz/menu/salads`,
 * `/uz/menu/national/soups`), never in component state. That is what makes a
 * filtered menu shareable, linkable, indexable and restorable with the back
 * button — the original app kept it in `useState`, so every filter was lost on
 * reload and no filtered view could be linked to.
 */

/** The route's optional catch-all segments, already decoded by Next.js. */
export type MenuFilterSegments = string[] | undefined;

/** Raised when the URL names a section or subsection that does not exist. */
export class UnknownMenuFilterError extends Error {
  constructor(segments: string[]) {
    super(`No menu category matches /${segments.join('/')}`);
    this.name = 'UnknownMenuFilterError';
  }
}

function findCategory(menu: MenuResponse, slug: string): MenuCategory | undefined {
  return menu.categories.find((category) => category.slug === slug);
}

function findSubcategory(
  category: MenuCategory,
  slug: string
): MenuSubcategory | undefined {
  return category.children.find((child) => child.slug === slug);
}

/**
 * Products of `category` that belong to `subcategorySlug`.
 *
 * A section's `products` array carries everything beneath it, and each product
 * names its own category — which is the subsection's slug when it has one.
 */
function productsInSubcategory(
  category: MenuCategory,
  subcategorySlug: string
): MenuProduct[] {
  return category.products.filter((product) => product.category_slug === subcategorySlug);
}

/**
 * Splits a section into one group per subsection, plus a leading group for the
 * products attached directly to the section itself. Groups that would be empty
 * are dropped, so a heading never appears above nothing.
 */
function groupBySubcategory(category: MenuCategory): ProductGroup[] {
  if (category.children.length === 0) {
    return category.products.length > 0
      ? [{slug: category.slug, name: category.name, products: category.products}]
      : [];
  }

  const direct = productsInSubcategory(category, category.slug);

  const groups: ProductGroup[] = direct.length
    ? [{slug: category.slug, name: category.name, products: direct}]
    : [];

  for (const child of category.children) {
    const products = productsInSubcategory(category, child.slug);
    if (products.length > 0) {
      groups.push({slug: child.slug, name: child.name, products});
    }
  }

  return groups;
}

function countProducts(groups: ProductGroup[]): number {
  return groups.reduce((total, group) => total + group.products.length, 0);
}

/**
 * Resolves the catch-all segments against the menu.
 *
 * @throws {UnknownMenuFilterError} when a segment names no existing category —
 * the caller turns this into a 404 rather than silently showing everything.
 */
export function resolveMenuView(menu: MenuResponse, segments: MenuFilterSegments): MenuView {
  const [categorySlug, subcategorySlug, ...rest] = segments ?? [];

  if (categorySlug === undefined) {
    const groups = menu.categories
      .filter((category) => category.products.length > 0)
      .map((category) => ({
        slug: category.slug,
        name: category.name,
        products: category.products
      }));

    return {category: null, subcategory: null, groups, productCount: countProducts(groups)};
  }

  // `/menu/a/b/c` is not a route this page can mean anything by.
  if (rest.length > 0) throw new UnknownMenuFilterError(segments ?? []);

  const category = findCategory(menu, categorySlug);
  if (!category) throw new UnknownMenuFilterError(segments ?? []);

  if (subcategorySlug === undefined) {
    const groups = groupBySubcategory(category);
    return {category, subcategory: null, groups, productCount: countProducts(groups)};
  }

  const subcategory = findSubcategory(category, subcategorySlug);
  if (!subcategory) throw new UnknownMenuFilterError(segments ?? []);

  const products = productsInSubcategory(category, subcategory.slug);

  return {
    category,
    subcategory,
    groups: products.length > 0 ? [{slug: subcategory.slug, name: subcategory.name, products}] : [],
    productCount: products.length
  };
}

/** Every product in the current view, flattened for search. */
export function flattenGroups(groups: ProductGroup[]): MenuProduct[] {
  return groups.flatMap((group) => group.products);
}

/**
 * Every filter path the menu can produce, as catch-all segment arrays:
 * `[]` for the whole menu, `[section]`, then `[section, subsection]`.
 * Feeds `generateStaticParams`, so each filter is prerendered rather than
 * rendered on demand.
 */
export function menuFilterPaths(menu: MenuResponse): string[][] {
  const paths: string[][] = [[]];

  for (const category of menu.categories) {
    paths.push([category.slug]);
    for (const child of category.children) {
      paths.push([category.slug, child.slug]);
    }
  }

  return paths;
}
