import {cookies, headers} from 'next/headers';
import {NextIntlClientProvider} from 'next-intl';
import type {ReactNode} from 'react';

import {LOCALE_COOKIE_NAME, negotiateLocale} from '@/features/tables/negotiate-locale';
import {getMessagesForLocale} from '@/i18n/messages';
import {fontVariables} from '@/lib/fonts';

import '../../../globals.css';

/**
 * Root layout for the dead-QR landing page.
 *
 * This branch of the router lives outside `[locale]`, so it cannot inherit that
 * segment's shell and needs its own `<html>`. That is the right shape anyway:
 * a guest whose sticker does not work wants one clear message and a way into
 * the menu, not a header full of navigation they did not ask for.
 */
export default async function ScanFallbackLayout({children}: {children: ReactNode}) {
  const [cookieStore, headerList] = await Promise.all([cookies(), headers()]);
  const locale = negotiateLocale(
    cookieStore.get(LOCALE_COOKIE_NAME)?.value,
    headerList.get('accept-language')
  );

  return (
    <html lang={locale} className={`${fontVariables} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        {/*
          Configured by hand rather than through `setRequestLocale`: this route
          has no `[locale]` segment, so `next-intl` would otherwise resolve the
          request to the default locale and the locale-aware `Link` would have
          no context to read at all.
        */}
        <NextIntlClientProvider
          locale={locale}
          messages={getMessagesForLocale(locale)}
          timeZone="Asia/Tashkent"
        >
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
