'use client';

import {useId, useMemo, useState} from 'react';
import {useTranslations} from 'next-intl';

import {Button, EmptyState, PillLink} from '@/components/ui';

import {MenuSearch} from './MenuSearch';
import {ProductGrid} from './ProductGrid';
import {filterProducts, toSearchTerms} from '../search';
import {flattenGroups} from '../selectors';
import type {ProductGroup} from '../types';
import {useDebouncedValue} from '../useDebouncedValue';

export interface MenuBrowserProps {
  /** Groups already resolved from the URL on the server, in menu order. */
  groups: ProductGroup[];
}

/** Pause after the last keystroke before the grid re-filters. */
const SEARCH_DEBOUNCE_MS = 200;

/**
 * The interactive half of the menu: search over the products the server already
 * sent for this route.
 *
 * Category filtering is *not* here — that lives in the URL and is resolved on
 * the server, so this component never has to know which section is active. All
 * it does is narrow the set it was handed, which is why searching costs no
 * request and works the moment the page becomes interactive.
 */
export function MenuBrowser({groups}: MenuBrowserProps) {
  const t = useTranslations('menu');
  const [query, setQuery] = useState('');
  const resultsId = useId();

  // Debounce the *filter*, never the input: the field stays instant while the
  // grid settles once typing pauses.
  const debouncedQuery = useDebouncedValue(query, SEARCH_DEBOUNCE_MS);

  const allProducts = useMemo(() => flattenGroups(groups), [groups]);

  const isSearching = toSearchTerms(debouncedQuery).length > 0;
  const results = useMemo(
    () => (isSearching ? filterProducts(allProducts, debouncedQuery) : []),
    [allProducts, debouncedQuery, isSearching]
  );

  return (
    <>
      <div className="mt-8">
        <MenuSearch onValueChange={setQuery} resultsId={resultsId} value={query} />
      </div>

      {/*
        Announced politely rather than assertively: the count changes as the
        user types, and an assertive region would interrupt them mid-word.
      */}
      <p
        aria-live="polite"
        className="mt-3 min-h-6 text-label text-muted normal-case tracking-normal"
        id={resultsId}
      >
        {isSearching
          ? t('search.resultCount', {count: results.length})
          : t('counts.dishes', {count: allProducts.length})}
      </p>

      {isSearching ? (
        results.length > 0 ? (
          <div className="mt-6">
            <ProductGrid products={results} />
          </div>
        ) : (
          <EmptyState
            action={
              <Button onClick={() => setQuery('')} variant="secondary">
                {t('search.clear')}
              </Button>
            }
            className="mt-6"
            description={t('search.noResultsDescription')}
            title={t('search.noResultsTitle', {query: debouncedQuery})}
          />
        )
      ) : groups.length > 0 ? (
        <div className="mt-6 flex flex-col gap-12">
          {groups.map((group, groupIndex) => (
            <GroupSection
              eagerFrom={eagerOffset(groups, groupIndex)}
              group={group}
              key={group.slug}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          action={<PillLink href="/menu">{t('empty.action')}</PillLink>}
          className="mt-6"
          description={t('empty.description')}
          title={t('empty.title')}
        />
      )}
    </>
  );
}

/**
 * How many products precede `groupIndex`. Feeding this to each grid is what
 * keeps "the first screenful loads eagerly" true across several stacked
 * sections instead of restarting the count at every heading.
 */
function eagerOffset(groups: ProductGroup[], groupIndex: number): number {
  let offset = 0;

  for (let index = 0; index < groupIndex; index += 1) {
    offset += groups[index].products.length;
  }

  return offset;
}

function GroupSection({group, eagerFrom}: {group: ProductGroup; eagerFrom: number}) {
  const headingId = `menu-group-${group.slug}`;

  return (
    <section aria-labelledby={headingId}>
      <div className="mb-4 flex items-baseline gap-4">
        <h2 className="font-display text-title text-gold-200" id={headingId}>
          {group.name}
        </h2>
        <hr className="rule-gold flex-1" />
      </div>

      <ProductGrid
        aria-labelledby={headingId}
        eagerFrom={eagerFrom}
        products={group.products}
      />
    </section>
  );
}
