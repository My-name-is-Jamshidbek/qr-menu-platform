'use client';

import {ProductCard} from './ProductCard';
import type {MenuProduct} from '../types';

export interface ProductGridProps {
  products: MenuProduct[];
  /**
   * How many of the page's leading images have already been marked eager by an
   * earlier grid. Cards below that count load lazily. Passing the running total
   * rather than a boolean is what keeps "the first screenful" correct when the
   * page renders several sections in a row.
   */
  eagerFrom?: number;
  /** Accessible name for the list, e.g. the section heading it sits under. */
  'aria-labelledby'?: string;
}

/**
 * Number of images loaded up front. Four fills the first viewport on a desktop
 * grid and overshoots comfortably on a phone, where only one card is visible.
 */
const EAGER_IMAGE_COUNT = 4;

/** The menu grid: 1 column on a phone, then 2, 3 and 4 as the viewport grows. */
export function ProductGrid({products, eagerFrom = 0, ...listProps}: ProductGridProps) {
  return (
    <ul
      className="grid list-none grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      role="list"
      {...listProps}
    >
      {products.map((product, index) => (
        <li key={product.slug}>
          <ProductCard eager={eagerFrom + index < EAGER_IMAGE_COUNT} product={product} />
        </li>
      ))}
    </ul>
  );
}
