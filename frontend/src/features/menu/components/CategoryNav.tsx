import {getTranslations} from 'next-intl/server';

import {PillLink} from '@/components/ui';

import type {MenuCategory, MenuSubcategory} from '../types';

export interface CategoryNavProps {
  categories: MenuCategory[];
  /** The section the URL selected, or `null` on the unfiltered menu. */
  activeCategory: MenuCategory | null;
  /** The subsection the URL selected, or `null` when a whole section is shown. */
  activeSubcategory: MenuSubcategory | null;
}

/**
 * Section and subsection filters, as real navigable links.
 *
 * Every filter is a URL — `/uz/menu`, `/uz/menu/salads`, `/uz/menu/national/soups`
 * — rendered on the server. That is the fix for the original app's central bug,
 * where the active category lived in `useState`: a filtered view could not be
 * linked to or shared, the back button skipped past it, a reload dropped the
 * guest back to "everything", and search engines only ever saw one page.
 *
 * `PillLink` sets `aria-current="page"` on the active entry, so the selection is
 * conveyed to assistive tech and not only by the gold fill.
 */
export async function CategoryNav({
  categories,
  activeCategory,
  activeSubcategory
}: CategoryNavProps) {
  const t = await getTranslations('menu.filters');

  return (
    <div className="flex flex-col gap-3">
      {/*
        `edge-fade-x` scrolls the strip horizontally on a phone and fades the
        overflowing ends instead of slicing a pill in half.
      */}
      <nav aria-label={t('categoriesLabel')} className="edge-fade-x -mx-gutter gutter-x">
        <ul className="flex list-none items-center gap-2 py-1" role="list">
          <li>
            <PillLink active={activeCategory === null} href="/menu">
              {t('all')}
            </PillLink>
          </li>

          {categories.map((category) => (
            <li key={category.slug}>
              <PillLink
                active={activeCategory?.slug === category.slug}
                href={`/menu/${category.slug}`}
              >
                {category.name}
              </PillLink>
            </li>
          ))}
        </ul>
      </nav>

      {/*
        The second strip only exists for a section that actually has subsections,
        so the row never appears as an empty band under the first one.
      */}
      {activeCategory && activeCategory.children.length > 0 ? (
        <nav
          aria-label={t('subcategoriesLabel', {category: activeCategory.name})}
          className="edge-fade-x -mx-gutter gutter-x"
        >
          <ul className="flex list-none items-center gap-2 py-1" role="list">
            <li>
              <PillLink
                active={activeSubcategory === null}
                href={`/menu/${activeCategory.slug}`}
              >
                {t('allInCategory')}
              </PillLink>
            </li>

            {activeCategory.children.map((child) => (
              <li key={child.slug}>
                <PillLink
                  active={activeSubcategory?.slug === child.slug}
                  href={`/menu/${activeCategory.slug}/${child.slug}`}
                >
                  {child.name}
                </PillLink>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
    </div>
  );
}
