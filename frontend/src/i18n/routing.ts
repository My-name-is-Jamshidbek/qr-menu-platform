import {defineRouting} from 'next-intl/routing';

/**
 * Locale routing. Keep `locales` in sync with `LOCALES` in
 * `scripts/generate-message-catalog.mjs` and with the `Language` choices in the
 * Django `menu` app.
 */
export const routing = defineRouting({
  locales: ['uz', 'ru', 'en'],
  defaultLocale: 'uz',
  // Every URL carries its locale (/uz, /ru, /en) — no unprefixed variant, so a
  // page has exactly one canonical URL per language and `/` redirects to `/uz`.
  localePrefix: 'always',
  localeDetection: true
});

export type AppLocale = (typeof routing.locales)[number];

export const locales = routing.locales;
export const defaultLocale = routing.defaultLocale;

export function isAppLocale(value: string | undefined): value is AppLocale {
  return value !== undefined && (locales as readonly string[]).includes(value);
}
