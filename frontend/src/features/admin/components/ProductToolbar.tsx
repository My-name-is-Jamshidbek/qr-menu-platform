import {getTranslations} from 'next-intl/server';

import {Button, Input, Select} from '@/components/ui';
import {Link} from '@/i18n/navigation';
import type {AppLocale} from '@/i18n/routing';

import {LIST_PARAMS} from '../constants';
import type {CategoryOption, ProductQuery} from '../types';

/**
 * Search and category filter.
 *
 * A plain `method="get"` form: submitting rewrites the query string, the page
 * re-renders on the server and one page of rows comes back. There is no
 * client-side filtering anywhere in the panel — the original shipped all 86
 * products to the browser and filtered them there, which is why it got slower
 * with every dish added. Leaving out a `page` field is deliberate: a new search
 * always starts at page one.
 */
export interface ProductToolbarProps {
  locale: AppLocale;
  query: ProductQuery;
  categories: readonly CategoryOption[];
}

export async function ProductToolbar({locale, query, categories}: ProductToolbarProps) {
  const t = await getTranslations({locale, namespace: 'admin.products'});

  return (
    <form
      method="get"
      role="search"
      className="flex flex-col gap-4 rounded-lg border border-ground-border bg-ground-surface p-4 sm:flex-row sm:items-end"
    >
      <Input
        label={t('searchLabel')}
        type="search"
        name={LIST_PARAMS.search}
        defaultValue={query.search}
        placeholder={t('searchPlaceholder')}
        autoComplete="off"
        className="flex-1"
      />

      <Select
        label={t('categoryLabel')}
        name={LIST_PARAMS.category}
        defaultValue={query.category}
        className="sm:w-64"
      >
        <option value="">{t('allCategories')}</option>
        {categories.map((category) => (
          <option key={category.id} value={category.slug}>
            {category.isChild ? `— ${category.label}` : category.label}
          </option>
        ))}
      </Select>

      <div className="flex gap-2">
        <Button type="submit" variant="secondary">
          {t('apply')}
        </Button>

        {query.search !== '' || query.category !== '' ? (
          <Link
            href="/admin/products"
            className="inline-flex min-h-11 items-center rounded-md px-4 text-label text-cream/70 uppercase hover:text-gold-200"
          >
            {t('reset')}
          </Link>
        ) : null}
      </div>
    </form>
  );
}
