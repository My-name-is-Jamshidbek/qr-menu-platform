import type {Metadata} from 'next';
import {notFound} from 'next/navigation';
import {NextIntlClientProvider} from 'next-intl';
import {getTranslations, setRequestLocale} from 'next-intl/server';

import {SiteFooter} from '@/components/layout/SiteFooter';
import {SiteHeader} from '@/components/layout/SiteHeader';
import {isAppLocale, routing} from '@/i18n/routing';
import {fontVariables} from '@/lib/fonts';

import '../globals.css';

/** Pre-renders one static shell per locale instead of rendering on demand. */
export function generateStaticParams() {
  return routing.locales.map((locale) => ({locale}));
}

export async function generateMetadata({params}: LayoutProps<'/[locale]'>): Promise<Metadata> {
  const {locale} = await params;

  if (!isAppLocale(locale)) notFound();

  const t = await getTranslations({locale, namespace: 'common.site'});

  return {
    title: {default: t('name'), template: `%s · ${t('name')}`},
    description: t('tagline'),
    metadataBase: process.env.NEXT_PUBLIC_SITE_URL
      ? new URL(process.env.NEXT_PUBLIC_SITE_URL)
      : null,
    alternates: {
      canonical: `/${locale}`,
      languages: Object.fromEntries(routing.locales.map((item) => [item, `/${item}`]))
    }
  };
}

export default async function LocaleLayout({children, params}: LayoutProps<'/[locale]'>) {
  const {locale} = await params;

  // The [locale] segment is effectively a catch-all, so an unknown value here
  // is an unknown route rather than a language we forgot to configure.
  if (!isAppLocale(locale)) notFound();

  setRequestLocale(locale);

  const t = await getTranslations({locale, namespace: 'common.nav'});

  return (
    <html lang={locale} className={`${fontVariables} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <NextIntlClientProvider>
          {/*
            First tab stop on every page. It is off-screen until focused, which
            is the only way a keyboard user can skip a sticky header that would
            otherwise sit in front of the content on every navigation.
          */}
          <a
            href="#main"
            className="sr-only-focusable top-4 left-4 z-50 rounded-md bg-gold-gradient px-4 py-2.5 text-label text-ink uppercase shadow-modal"
          >
            {t('skipToContent')}
          </a>
          <SiteHeader />
          {/*
            The skip-link target lives here rather than on each page's <main>,
            so a new route cannot forget it and silently break the shortcut.
          */}
          <div id="main" className="flex flex-1 flex-col">
            {children}
          </div>
          <SiteFooter />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
