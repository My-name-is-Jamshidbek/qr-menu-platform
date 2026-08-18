import {getFormatter, getTranslations} from 'next-intl/server';

import {Badge} from '@/components/ui';
import {Link} from '@/i18n/navigation';
import type {AppLocale} from '@/i18n/routing';

import {moveProductAction} from '../actions';
import {REQUIRED_CONTENT_LANGUAGE, type ContentLanguage} from '../constants';
import {translatedName} from '../data';
import type {AdminProduct, CategoryOption, ProductQuery} from '../types';

import {DeleteProductButton} from './DeleteProductButton';
import {SubmitButton} from './SubmitButton';

/**
 * The product list.
 *
 * A real `<table>`: the data is tabular, and a table gives row and column
 * headers to a screen reader for free. Only the current page of rows is
 * rendered — paging and searching happen on the server.
 */
export interface ProductTableProps {
  locale: AppLocale;
  products: readonly AdminProduct[];
  categories: readonly CategoryOption[];
  query: ProductQuery;
}

const CELL = 'px-3 py-3 align-middle';
const HEAD_CELL = 'px-3 py-2 text-label text-gold-200 uppercase whitespace-nowrap';

/** Up/down arrow, mirrored with a transform so one path serves both. */
function ArrowIcon({direction}: {direction: 'up' | 'down'}) {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={direction === 'down' ? 'size-4 rotate-180' : 'size-4'}
      aria-hidden="true"
    >
      <path d="M8 13V3M3.5 7.5 8 3l4.5 4.5" />
    </svg>
  );
}

export async function ProductTable({locale, products, categories, query}: ProductTableProps) {
  const t = await getTranslations({locale, namespace: 'admin.products'});
  const format = await getFormatter({locale});

  const categoryLabels = new Map(categories.map((category) => [category.id, category.label]));

  return (
    <div className="overflow-x-auto rounded-lg border border-ground-border bg-ground-surface">
      <table className="w-full min-w-[52rem] border-collapse text-body">
        <thead className="border-b border-ground-border">
          <tr>
            <th scope="col" className={`${HEAD_CELL} text-left`}>
              {t('columns.name')}
            </th>
            <th scope="col" className={`${HEAD_CELL} text-left`}>
              {t('columns.category')}
            </th>
            <th scope="col" className={`${HEAD_CELL} text-right`}>
              {t('columns.price')}
            </th>
            <th scope="col" className={`${HEAD_CELL} text-left`}>
              {t('columns.availability')}
            </th>
            <th scope="col" className={`${HEAD_CELL} text-left`}>
              {t('columns.languages')}
            </th>
            <th scope="col" className={`${HEAD_CELL} text-center`}>
              {t('columns.order')}
            </th>
            <th scope="col" className={`${HEAD_CELL} text-right`}>
              {t('columns.actions')}
            </th>
          </tr>
        </thead>

        <tbody>
          {products.map((product) => {
            const displayName = translatedName(product.translations, locale) || t('noName');
            const primaryName =
              product.translations.find((row) => row.language === REQUIRED_CONTENT_LANGUAGE)?.name ??
              '';
            const missing = product.missing_translations as ContentLanguage[];

            return (
              <tr
                key={product.id}
                className="border-b border-ground-border/60 last:border-b-0 hover:bg-ground-elevated/60"
              >
                <th scope="row" className={`${CELL} text-left font-normal`}>
                  <Link
                    href={`/admin/products/${product.id}`}
                    className="font-display text-card text-cream hover:text-gold-200"
                  >
                    {displayName}
                  </Link>
                  {primaryName && primaryName !== displayName ? (
                    <span className="block text-label text-muted normal-case tracking-normal">
                      {primaryName}
                    </span>
                  ) : null}
                </th>

                <td className={CELL}>
                  <span className="text-label text-cream/70 normal-case tracking-normal">
                    {categoryLabels.get(product.category) ?? t('uncategorised')}
                  </span>
                </td>

                <td className={`${CELL} text-right`}>
                  <span className="tabular font-display text-price text-gold-200">
                    {format.number(product.price, {
                      style: 'currency',
                      currency: 'UZS',
                      maximumFractionDigits: 0
                    })}
                  </span>
                </td>

                <td className={CELL}>
                  <Badge tone={product.is_available ? 'success' : 'neutral'}>
                    {product.is_available ? t('available') : t('hidden')}
                  </Badge>
                </td>

                <td className={CELL}>
                  {missing.length === 0 ? (
                    <Badge tone="outline">{t('complete')}</Badge>
                  ) : (
                    <Badge tone="warning">
                      {t('missing', {languages: missing.join(', ').toUpperCase()})}
                    </Badge>
                  )}
                </td>

                <td className={CELL}>
                  <div className="flex items-center justify-center gap-1">
                    {(['up', 'down'] as const).map((direction) => (
                      <form key={direction} action={moveProductAction}>
                        <input type="hidden" name="locale" value={locale} />
                        <input type="hidden" name="id" value={product.id} />
                        <input type="hidden" name="direction" value={direction} />
                        <input type="hidden" name="category" value={query.category} />
                        <SubmitButton
                          variant="ghost"
                          size="sm"
                          data-testid={`admin-move-${direction}`}
                          className="px-2"
                          aria-label={t(direction === 'up' ? 'moveUp' : 'moveDown', {
                            name: displayName
                          })}
                          label=""
                          iconStart={<ArrowIcon direction={direction} />}
                        />
                      </form>
                    ))}
                  </div>
                </td>

                <td className={`${CELL} text-right`}>
                  <div className="flex items-center justify-end gap-1">
                    <Link
                      href={`/admin/products/${product.id}`}
                      aria-label={t('editNamed', {name: displayName})}
                      className="inline-flex min-h-11 items-center rounded-md px-3 text-label text-gold-200 uppercase hover:bg-gold-900/40"
                    >
                      {t('edit')}
                    </Link>
                    <DeleteProductButton
                      locale={locale}
                      productId={product.id}
                      productName={displayName}
                    />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
