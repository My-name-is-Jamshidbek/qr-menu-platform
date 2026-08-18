import {getTranslations, setRequestLocale} from 'next-intl/server';

import {isAppLocale, defaultLocale} from '@/i18n/routing';

/**
 * Placeholder home page. The design system and page agents replace the body of
 * this route; it exists so the locale shell is reachable and buildable.
 */
export default async function HomePage({params}: PageProps<'/[locale]'>) {
  const {locale} = await params;
  const resolvedLocale = isAppLocale(locale) ? locale : defaultLocale;

  setRequestLocale(resolvedLocale);
  const t = await getTranslations('common');

  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col justify-center px-[clamp(1rem,4vw,2rem)] py-24">
      <h1 className="font-display text-5xl font-semibold tracking-tight">{t('site.name')}</h1>
      <p className="mt-4 text-lg opacity-80">{t('site.tagline')}</p>
    </main>
  );
}
