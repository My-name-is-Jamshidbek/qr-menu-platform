import assert from 'node:assert/strict';
import {test} from 'node:test';

import {formatPrice, formatPriceAmount} from './format.ts';

/* See the note in `search.test.mjs` for why these tests are `.mjs`. */

const NBSP = ' ';

test('groups thousands with a no-break space in uz and ru', () => {
  assert.equal(formatPriceAmount(30000, 'uz'), `30${NBSP}000`);
  assert.equal(formatPriceAmount(30000, 'ru'), `30${NBSP}000`);
});

test('groups thousands with a comma in en', () => {
  assert.equal(formatPriceAmount(30000, 'en'), '30,000');
});

test('leaves values under a thousand ungrouped', () => {
  assert.equal(formatPriceAmount(900, 'uz'), '900');
  assert.equal(formatPriceAmount(0, 'uz'), '0');
});

test('groups every three digits, not just the first break', () => {
  assert.equal(formatPriceAmount(1234567, 'uz'), `1${NBSP}234${NBSP}567`);
  assert.equal(formatPriceAmount(100000, 'uz'), `100${NBSP}000`);
});

test('an unknown locale falls back to the default separator', () => {
  assert.equal(formatPriceAmount(30000, 'de'), `30${NBSP}000`);
});

test('the currency is joined with a no-break space', () => {
  assert.equal(formatPrice(30000, 'uz', "so'm"), `30${NBSP}000${NBSP}so'm`);
});

/*
 * The guard that matters: this string is built once by Node while rendering and
 * again by the browser while hydrating. Anything ICU-dependent would differ
 * between the two and make React throw the markup away.
 */
test('formatting is independent of the runtime locale data', () => {
  const viaIntl = new Intl.NumberFormat('uz', {maximumFractionDigits: 0}).format(30000);
  const ours = formatPriceAmount(30000, 'uz');

  assert.equal(ours, `30${NBSP}000`);
  // Documents that we deliberately do not delegate to Intl here.
  assert.equal(typeof viaIntl, 'string');
});
