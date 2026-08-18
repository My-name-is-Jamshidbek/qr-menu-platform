import type {Metadata} from 'next';
import {notFound} from 'next/navigation';
import {getTranslations, setRequestLocale} from 'next-intl/server';

import {EmptyState, Toast} from '@/components/ui';
import {
  LIST_PARAMS,
  ProductPagination,
  ProductTable,
  ProductToolbar,
  fetchCategories,
  fetchProductPage,
  toCategoryOptions,
  type ProductQuery
} from '@/features/admin';
import {Link} from '@/i18n/navigation';
import {isAppLocale} from '@/i18n/routing';

/**
 * The product list: one server-rendered page of rows, filtered and paged on
 * the server. The original shipped every product to the browser on load.
 */

export async function generateMetadata({
  params
}: PageProps<'/[locale]/admin/products'>): Promise<Metadata> {
  const {locale} = await params;
  if (!isAppLocale(locale)) notFound();

  const t = await getTranslations({locale, namespace: 'admin.products'});
  return {title: t('title')};
}

/**
 * A link styled as the primary button. An `<a>` rather than a `<button>`
 * because it navigates — and nesting a button inside a link would be invalid
 * markup with two competing hit targets, which is one way an action ends up
 * unclickable.
 */
const PRIMARY_LINK_CLASSES =
  'inline-flex min-h-13 cursor-pointer items-center justify-center gap-2 rounded-md ' +
  'border border-gold-600/60 bg-gold-gradient px-7 py-3 font-display text-card text-ink ' +
  'shadow-card transition-[filter] duration-[var(--motion-base)] ease-out hover:brightness-110';

function readParam(value: string | string[] | undefined): string {
  return typeof value === 'string' ? value : '';
}

export default async function AdminProductsPage({
  params,
  searchParams
}: PageProps<'/[locale]/admin/products'>) {
  const {locale} = await params;
  if (!isAppLocale(locale)) notFound();

  setRequestLocale(locale);

  const t = await getTranslations({locale, namespace: 'admin.products'});
  const tCommon = await getTranslations({locale, namespace: 'common'});
  const resolved = await searchParams;

  const query: ProductQuery = {
    page: Math.max(1, Number.parseInt(readParam(resolved[LIST_PARAMS.page]), 10) || 1),
    search: readParam(resolved[LIST_PARAMS.search]).trim(),
    category: readParam(resolved[LIST_PARAMS.category]).trim()
  };

  const [categories, page] = await Promise.all([fetchCategories(), fetchProductPage(query)]);
  const options = toCategoryOptions(categories, locale);
  const isFiltered = query.search !== '' || query.category !== '';

  return (
    <section className="flex flex-col gap-6">
      {/*
        The primary action sits in normal document flow next to the heading.
        Nothing in the panel is sticky or absolutely positioned over this row,
        which is what stopped the original's "add product" button from ever
        being clickable.
      */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="font-display text-title text-cream">{t('title')}</h1>
          <p className="text-body text-muted">
            {isFiltered ? t('resultCount', {count: page.count}) : t('subtitle', {count: page.count})}
          </p>
        </div>

        <Link
          href="/admin/products/new"
          data-testid="admin-create-product"
          className={PRIMARY_LINK_CLASSES}
        >
          {t('create')}
        </Link>
      </div>

      {resolved.deleted === '1' ? (
        <Toast
          message={t('deleted')}
          tone="success"
          closeLabel={tCommon('actions.close')}
          className="w-full"
        />
      ) : null}

      <ProductToolbar locale={locale} query={query} categories={options} />

      {page.items.length === 0 ? (
        <EmptyState
          title={isFiltered ? t('empty.searchTitle') : t('empty.title')}
          description={isFiltered ? t('empty.searchDescription') : t('empty.description')}
          action={
            <Link href="/admin/products/new" className={PRIMARY_LINK_CLASSES}>
              {t('create')}
            </Link>
          }
        />
      ) : (
        <>
          <ProductTable
            locale={locale}
            products={page.items}
            categories={options}
            query={query}
          />
          <ProductPagination
            locale={locale}
            page={page.page}
            pageCount={page.pageCount}
            query={query}
          />
        </>
      )}
    </section>
  );
}
