import {getTranslations} from 'next-intl/server';

import {Link} from '@/i18n/navigation';
import type {AppLocale} from '@/i18n/routing';
import {cn} from '@/lib/cn';

import {LIST_PARAMS} from '../constants';
import type {ProductQuery} from '../types';

/**
 * Page controls for the product list.
 *
 * Real links carrying the current filters, so a page is shareable, the browser
 * Back button behaves, and the whole thing still works before any JavaScript
 * has loaded. The neighbouring page numbers are rendered too, because "page 4
 * of 6" with only arrows makes jumping back to the start needlessly tedious.
 */
export interface ProductPaginationProps {
  locale: AppLocale;
  page: number;
  pageCount: number;
  query: ProductQuery;
}

const LINK_CLASSES =
  'inline-flex min-h-11 min-w-11 items-center justify-center rounded-md px-3 text-label uppercase ' +
  'border border-ground-border text-cream/75 transition-colors duration-[var(--motion-fast)] ' +
  'hover:border-gold-700 hover:text-gold-200';

const DISABLED_CLASSES =
  'inline-flex min-h-11 min-w-11 items-center justify-center rounded-md px-3 text-label uppercase ' +
  'border border-ground-border/50 text-muted';

export async function ProductPagination({locale, page, pageCount, query}: ProductPaginationProps) {
  const t = await getTranslations({locale, namespace: 'admin.products'});

  if (pageCount <= 1) return null;

  const hrefFor = (targetPage: number): string => {
    const params = new URLSearchParams();
    if (query.search) params.set(LIST_PARAMS.search, query.search);
    if (query.category) params.set(LIST_PARAMS.category, query.category);
    if (targetPage > 1) params.set(LIST_PARAMS.page, String(targetPage));

    const search = params.toString();
    return search ? `/admin/products?${search}` : '/admin/products';
  };

  // A short window around the current page: enough to step through a long list
  // without turning the footer into a wall of numbers.
  const first = Math.max(1, Math.min(page - 2, pageCount - 4));
  const numbers = Array.from({length: Math.min(5, pageCount)}, (_, index) => first + index);

  return (
    <nav
      aria-label={t('pageOf', {page, pageCount})}
      className="flex flex-wrap items-center justify-between gap-3"
    >
      <p className="text-label text-muted normal-case tracking-normal">
        {t('pageOf', {page, pageCount})}
      </p>

      <ul className="flex flex-wrap items-center gap-2">
        <li>
          {page > 1 ? (
            <Link href={hrefFor(page - 1)} className={LINK_CLASSES} rel="prev">
              {t('previous')}
            </Link>
          ) : (
            <span className={DISABLED_CLASSES} aria-disabled="true">
              {t('previous')}
            </span>
          )}
        </li>

        {numbers.map((number) => (
          <li key={number}>
            <Link
              href={hrefFor(number)}
              aria-current={number === page ? 'page' : undefined}
              className={cn(
                LINK_CLASSES,
                'tabular',
                number === page && 'bg-gold-gradient text-ink hover:text-ink'
              )}
            >
              {number}
            </Link>
          </li>
        ))}

        <li>
          {page < pageCount ? (
            <Link href={hrefFor(page + 1)} className={LINK_CLASSES} rel="next">
              {t('next')}
            </Link>
          ) : (
            <span className={DISABLED_CLASSES} aria-disabled="true">
              {t('next')}
            </span>
          )}
        </li>
      </ul>
    </nav>
  );
}
