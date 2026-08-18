import {getRequestConfig} from 'next-intl/server';

import {getMessagesForLocale} from './messages';
import {defaultLocale, isAppLocale} from './routing';

/**
 * Per-request i18n configuration consumed by `next-intl`.
 *
 * `requestLocale` is used rather than `next/root-params` because this runs for
 * Route Handlers and Server Actions too, where root params are unavailable.
 * The `[locale]` segment acts as a catch-all, so unknown values (e.g. a stray
 * `/favicon.ico` request) are coerced to the default locale.
 */
export default getRequestConfig(async ({requestLocale}) => {
  const requested = await requestLocale;
  const locale = isAppLocale(requested) ? requested : defaultLocale;

  return {
    locale,
    messages: getMessagesForLocale(locale),
    timeZone: 'Asia/Tashkent'
  };
});
