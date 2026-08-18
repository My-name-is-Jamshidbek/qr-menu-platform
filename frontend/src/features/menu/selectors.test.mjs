import assert from 'node:assert/strict';
import {test} from 'node:test';

import {
  flattenGroups,
  menuFilterPaths,
  resolveMenuView,
  UnknownMenuFilterError
} from './selectors.ts';

/* See the note in `search.test.mjs` for why these tests are `.mjs`. */

/** @returns {import('./types.ts').MenuProduct} */
function product(slug, categorySlug) {
  return {
    slug,
    name: slug,
    description: '',
    is_fallback: false,
    price: 30000,
    category_slug: categorySlug,
    image: null
  };
}

/**
 * Mirrors the real payload: a section's `products` array holds everything
 * beneath it, and each product names its own category — the subsection's slug
 * when it has one, the section's slug otherwise.
 *
 * @type {import('./types.ts').MenuResponse}
 */
const menu = {
  generated_at: '2026-08-18T10:00:00Z',
  categories: [
    {
      slug: 'national',
      name: 'Milliy taomlar',
      is_fallback: false,
      children: [
        {slug: 'main-courses', name: 'Asosiy taomlar', is_fallback: false},
        {slug: 'soups', name: 'Shoʻrvalar', is_fallback: false}
      ],
      products: [
        product('gosht-say', 'main-courses'),
        product('mastava', 'soups'),
        product('milliy-set', 'national')
      ]
    },
    {
      slug: 'salads',
      name: 'Salatlar',
      is_fallback: false,
      children: [],
      products: [product('boss-salat', 'salads')]
    },
    {
      slug: 'empty-section',
      name: 'Boʻsh',
      is_fallback: false,
      children: [],
      products: []
    }
  ]
};

test('no filter groups every non-empty section', () => {
  const view = resolveMenuView(menu, undefined);

  assert.equal(view.category, null);
  assert.equal(view.subcategory, null);
  assert.deepEqual(
    view.groups.map((group) => group.slug),
    ['national', 'salads']
  );
  assert.equal(view.productCount, 4);
});

test('a section without children yields one group', () => {
  const view = resolveMenuView(menu, ['salads']);

  assert.equal(view.category?.slug, 'salads');
  assert.equal(view.subcategory, null);
  assert.deepEqual(
    view.groups.map((group) => group.slug),
    ['salads']
  );
});

test('a section with children lists its own products first, then subsections', () => {
  const view = resolveMenuView(menu, ['national']);

  assert.deepEqual(
    view.groups.map((group) => group.slug),
    ['national', 'main-courses', 'soups']
  );
  assert.deepEqual(
    view.groups.map((group) => group.products.length),
    [1, 1, 1]
  );
  assert.equal(view.productCount, 3);
});

test('a subsection filter keeps only that subsection', () => {
  const view = resolveMenuView(menu, ['national', 'soups']);

  assert.equal(view.category?.slug, 'national');
  assert.equal(view.subcategory?.slug, 'soups');
  assert.deepEqual(
    view.groups.map((group) => group.products.map((item) => item.slug)),
    [['mastava']]
  );
});

test('an empty section resolves to no groups, so the page shows its empty state', () => {
  const view = resolveMenuView(menu, ['empty-section']);

  assert.deepEqual(view.groups, []);
  assert.equal(view.productCount, 0);
});

test('unknown segments are rejected so the route can 404', () => {
  assert.throws(() => resolveMenuView(menu, ['nope']), UnknownMenuFilterError);
  assert.throws(() => resolveMenuView(menu, ['salads', 'nope']), UnknownMenuFilterError);
  assert.throws(
    () => resolveMenuView(menu, ['national', 'soups', 'extra']),
    UnknownMenuFilterError
  );
});

test('flattenGroups concatenates in group order', () => {
  const view = resolveMenuView(menu, ['national']);

  assert.deepEqual(
    flattenGroups(view.groups).map((item) => item.slug),
    ['milliy-set', 'gosht-say', 'mastava']
  );
});

test('menuFilterPaths covers the whole menu, every section and every subsection', () => {
  assert.deepEqual(menuFilterPaths(menu), [
    [],
    ['national'],
    ['national', 'main-courses'],
    ['national', 'soups'],
    ['salads'],
    ['empty-section']
  ]);
});
