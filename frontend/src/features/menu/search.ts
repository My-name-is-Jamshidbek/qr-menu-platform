import type {MenuProduct} from './types';

/**
 * Client-side menu search.
 *
 * The whole menu is already in memory (one `GET /menu/` for ~105 products), so
 * filtering here costs nothing and answers instantly — no request per keystroke.
 *
 * The folding rules deliberately mirror `apps/common/api/search.fold()` on the
 * Django side, so typing the same words into this box and into
 * `GET /products/?search=` gives the same matches:
 *
 *   - accents are dropped from Latin letters (é → e)
 *   - Cyrillic `ё` folds to `е`, but `й` is left alone — folding it would merge
 *     genuinely different words
 *   - the Uzbek apostrophe variants in `oʻ` / `gʻ` are deleted outright, because
 *     staff and guests each type whichever mark their keyboard offers
 *   - matching is case-insensitive
 */

/** Apostrophe-like marks that carry no distinction in Uzbek Latin. */
const DELETED_MARKS = /['’ʻʼʽ`´]/g;

/** A combining mark that follows an ASCII letter, i.e. a Latin accent. */
const LATIN_ACCENT = /([A-Za-z])\p{Mn}+/gu;

/**
 * Lowercased, unaccented, apostrophe-free form of `text`.
 *
 * Decomposing to NFD and recomposing to NFC afterwards is what keeps `й`
 * intact: its combining breve is only stripped when the base letter is ASCII.
 */
export function fold(text: string): string {
  return text
    .replace(/ё/g, 'е')
    .replace(/Ё/g, 'Е')
    .normalize('NFD')
    .replace(LATIN_ACCENT, '$1')
    .normalize('NFC')
    .replace(DELETED_MARKS, '')
    .toLowerCase();
}

/**
 * Splits a query into folded terms. Every term must match for a product to
 * qualify, so "issiq lagmon" narrows rather than widens.
 */
export function toSearchTerms(query: string): string[] {
  return fold(query).split(/\s+/).filter(Boolean);
}

/** The text of a product that search looks at: its name and its description. */
function searchableText(product: MenuProduct): string {
  return fold(`${product.name} ${product.description}`);
}

/**
 * Products matching every term in `query`, in their original menu order.
 * An empty or whitespace-only query returns the input untouched.
 */
export function filterProducts(products: MenuProduct[], query: string): MenuProduct[] {
  const terms = toSearchTerms(query);

  if (terms.length === 0) return products;

  return products.filter((product) => {
    const haystack = searchableText(product);
    return terms.every((term) => haystack.includes(term));
  });
}
