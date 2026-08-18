import assert from 'node:assert/strict';
import {test} from 'node:test';

import {filterProducts, fold, toSearchTerms} from './search.ts';

/*
 * Written as `.mjs` rather than `.ts` on purpose: `tsconfig.json` compiles every
 * `.ts` file in the project and does not enable `allowImportingTsExtensions`, so
 * a TypeScript test importing `./search.ts` would fail `next build`. Node 24
 * strips the types off the imported modules, so the code under test is still the
 * real, typed implementation.
 *
 * Run with: node --test "src/features/menu/*.test.mjs"
 */

/** @returns {import('./types.ts').MenuProduct} */
function product(name, description = '') {
  return {
    slug: name.toLowerCase().replace(/\s+/g, '-'),
    name,
    description,
    is_fallback: false,
    price: 30000,
    category_slug: 'salads',
    image: null
  };
}

test('fold lowercases and strips Latin accents', () => {
  assert.equal(fold('Café CRÈME'), 'cafe creme');
});

test('fold deletes every Uzbek apostrophe variant', () => {
  // The same word as staff and guests actually type it, across keyboards.
  for (const spelling of ["Lag'mon", 'Lagʻmon', 'Lagʼmon', 'Lag`mon', 'Lagmon']) {
    assert.equal(fold(spelling), 'lagmon', `failed for ${spelling}`);
  }
});

test('fold maps Cyrillic yo to ye but leaves short i alone', () => {
  // Mirrors the backend: ё/е are interchangeable in practice, и/й are not.
  assert.equal(fold('Ёлка'), 'елка');
  assert.equal(fold('чай'), 'чай');
  assert.notEqual(fold('чай'), fold('чаи'));
});

test('toSearchTerms splits on whitespace and drops empties', () => {
  assert.deepEqual(toSearchTerms('  issiq   lagmon '), ['issiq', 'lagmon']);
  assert.deepEqual(toSearchTerms('   '), []);
});

test('filterProducts returns the input for an empty query', () => {
  const products = [product('Boss salat'), product('Achichuk')];
  assert.deepEqual(filterProducts(products, '   '), products);
});

test('filterProducts matches regardless of apostrophe spelling', () => {
  const products = [product("Lag'mon"), product('Somsa')];

  assert.deepEqual(
    filterProducts(products, 'lagmon').map((item) => item.name),
    ["Lag'mon"]
  );
});

test('filterProducts requires every term to match', () => {
  const products = [product('Issiq lagmon', 'qaynoq'), product('Sovuq lagmon', 'muzdek')];

  assert.deepEqual(
    filterProducts(products, 'lagmon issiq').map((item) => item.name),
    ['Issiq lagmon']
  );
});

test('filterProducts searches the description too', () => {
  const products = [product('Boss salat', 'pomidor va bodring')];

  assert.equal(filterProducts(products, 'bodring').length, 1);
  assert.equal(filterProducts(products, 'kartoshka').length, 0);
});

test('filterProducts preserves menu order', () => {
  const products = [product('Salat bir'), product('Somsa'), product('Salat ikki')];

  assert.deepEqual(
    filterProducts(products, 'salat').map((item) => item.name),
    ['Salat bir', 'Salat ikki']
  );
});
