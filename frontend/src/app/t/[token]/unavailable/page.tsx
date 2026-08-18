import type {Metadata} from 'next';
import {cookies, headers} from 'next/headers';
import {getTranslations} from 'next-intl/server';

import {Container} from '@/components/layout';
import {EmptyState, PillLink} from '@/components/ui';
import {LOCALE_COOKIE_NAME, negotiateLocale} from '@/features/tables/negotiate-locale';
import type {AppLocale} from '@/i18n/routing';

/**
 * Where a scan lands when its token resolves to nothing.
 *
 * The scan route redirects here for an unknown token, a table taken out of
 * service, a throttled scan and an unreachable API alike — a guest holding a
 * phone gets a sentence and a link, never a stack trace or a bare 404.
 */

/**
 * Resolves the language from the same signals the scan route used.
 *
 * The page is outside the `[locale]` segment, so there is no route param to
 * read; `next-intl` would otherwise fall back to the default locale and greet a
 * Russian-speaking guest in Uzbek.
 */
async function resolveLocale(): Promise<AppLocale> {
  const [cookieStore, headerList] = await Promise.all([cookies(), headers()]);

  return negotiateLocale(
    cookieStore.get(LOCALE_COOKIE_NAME)?.value,
    headerList.get('accept-language')
  );
}

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations({locale: await resolveLocale(), namespace: 'tables.scan'});

  // A retired sticker is not a page worth indexing.
  return {title: t('metaTitle'), robots: {index: false, follow: false}};
}

export default async function TableUnavailablePage() {
  const locale = await resolveLocale();
  const t = await getTranslations({locale, namespace: 'tables.scan'});

  return (
    <Container as="main" className="flex flex-1 items-center py-16">
      <EmptyState
        className="w-full"
        title={t('unavailableTitle')}
        description={t('unavailableDescription')}
        icon={
          <svg
            viewBox="0 0 32 32"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
            className="size-7"
            aria-hidden="true"
          >
            <rect x="5" y="5" width="9" height="9" rx="1.5" />
            <rect x="18" y="5" width="9" height="9" rx="1.5" />
            <rect x="5" y="18" width="9" height="9" rx="1.5" />
            <path d="M18 18h4M27 22v5M18 27h9" />
          </svg>
        }
        action={
          // `locale` is passed explicitly: this route has no locale segment for
          // the navigation helper to infer the prefix from.
          <PillLink href="/menu" locale={locale} active>
            {t('openMenu')}
          </PillLink>
        }
      />
    </Container>
  );
}
